import asyncio

import datetime
import logging

import pyodbc
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, message
from aiogram.types.message import *
from aiogram.utils.markdown import link, hlink

# Импортируем настройки
from config import DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, \
	APPLICATION_NAME, BANK_TOKEN, CHANNEL_ID, USERS_ID_LIST, ADMIN_ID_LIST, TOKEN

from sql import checkPhone, checkUserExists, addUser, updateUser, delPhone, delUser, getContractCode, getBalance,\
	getPayments, getLastPayment, setSendStatus, getTechClaims, getContractCodeByUserId, getLastTechClaims,\
	getClientCodeByContractCode, getPromisedPayDate
# Импортируем адреса офисов и режим работы
from office import office_address

# Включим логирование

logging.basicConfig(level=logging.DEBUG)#, filename="DEBUG_log.log", filemode="a", format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

# Отдадим боту его токен
bot = Bot(TOKEN)  # Для aiogram
dp = Dispatcher()

# Объявим строку подключения к БД
conn_str = ';'.join([DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, APPLICATION_NAME])

#Получим список пользователей с расширенными правами(менеджеры)
manager_ids = {v:i for i, v in enumerate(eval(USERS_ID_LIST))}

#Получим список пользователей с админскими правами
admin_ids = {v:i for i, v in enumerate(eval(ADMIN_ID_LIST))}

#prices


# Объявили ветку для работы по команде 'start'
@dp.message(commands=['start'])
async def start(message):
	chat_id = message.chat.id
	user_id = message.from_user.id
	# проверим существование записи с user_id
	exist = f_checkUserExists(user_id)
	if str(exist[0]) == "1" and user_id == chat_id:
		# если запись существует, проверим можно ли использовать телефон
		check_grant = f_get_grant_on_phone(user_id)
		if check_grant != "Null" or check_grant is not None:
			for row in check_grant:
				grant_result = row[0]
				if grant_result == "1":
					button_phone = [
						[types.KeyboardButton(text='Мой баланс', request_contact=True)],
						[types.KeyboardButton(text='Мои заявки в тех.поддержку')],
						[types.KeyboardButton(text='Получить "Доверительный платеж"')]
					]
					keyboard = ReplyKeyboardMarkup(keyboard=button_phone, resize_keyboard=True)
					await bot.send_message(message.from_user.id, 'Выберите нужный пункт ниже', reply_markup=keyboard)
				elif grant_result == "0" or grant_result is None:
					button_phone = [[types.KeyboardButton(text="Отправить телефон", request_contact=True)]]
					keyboard = ReplyKeyboardMarkup(keyboard=button_phone, resize_keyboard=True)
					await bot.send_message(message.from_user.id, 'Вы еще не передали свой номер телефона,'
					                                             ' отправьте нам его нажав кнопку внизу.'
					                       , reply_markup=keyboard)
		elif check_grant == "Null" or check_grant is None:
			button_phone = [[types.KeyboardButton(text="Отправить контакт и узнать баланс", request_contact=True)]]
			keyboard = ReplyKeyboardMarkup(keyboard=button_phone, resize_keyboard=True)
			await bot.send_message(message.chat.id,
			                       'Этот бот может отобразить баланс вашего лицевого счета. Для этого нажмите кнопку ниже.'
			                       'Чтобы бот вам ответил, номер вашего телефона должен быть зарегистрирован в личном кабинете'
			                       ' абонента https://bill.sv-tel.ru ', reply_markup=keyboard)
	elif str(exist[0]) == "0" or str(exist[0]) == "Null" or user_id != chat_id:
		f_addUser(user_id, chat_id)  # добавим нового пользователя
		await bot.send_message(
			message.chat.id,
			'Этот бот может отобразить баланс вашего лицевого счета. Для этого нажмите кнопку ниже.'
			'Чтобы бот вам ответил, номер вашего телефона должен быть зарегистрирован в личном кабинете'
			' абонента https://bill.sv-tel.ru '
		)
		await bot.send_message(
			message.from_user.id, "Сохранили ваш Telegram ID в базу, нажмите /start для обновления"
		)


@dp.message(content_types=['contact'])  # Получили контактные данные
async def contact(message):  # Проверка отправителя и отправленного объекта
	if message.contact is not None and message.contact.user_id == message.chat.id or manager_ids.get(message.from_user.id) is not None:
		user_exist_check = f_checkUserExists(message.from_user.id)
		if str(user_exist_check[0]) == "1":
			checkPhone = f_get_grant_on_phone(message.from_user.id)
			if checkPhone != "Null" or checkPhone is not None:
				for row in checkPhone:
					checkPhone_result = row[0]
					if checkPhone_result == "1":
						global phonenumber, user_id, chat_id, nowDateTime, contract_code, contract, c_code
						phonenumber = message.contact.phone_number
						user_id = message.contact.user_id
						chat_id = message.chat.id
						nowDateTime = datetime.datetime.now()
						c_code = f_contract_code(phonenumber)
						if c_code is None:
							await bot.send_message(message.chat.id,
							                       'Номер телефона не найден в биллинговой системе ООО "Связист".'
							                       ' Зарегистрируйте его в '
							                       + '[личном кабинете](https://bill.sv-tel.ru)'
							                       + ' в разделе "Заявления - Получение уведомлений"',parse_mode='Markdown')
						else:
							for row in c_code:
								contract_code = row[0]
								f_updateUser(phonenumber, contract_code, user_id, chat_id)
								contract = row[1]
								payments = f_get_payments(contract_code)
								if contract_code is not None and contract_code != 50323:  # отработаем принадлежность к л/с 500
									for row in c_code:
										try:
											await bot.send_message(message.chat.id,
											                       'Ваш лицевой счет: ' + "%d" % (row[1]))
											balance = f_get_balance(row[0])
											try:
												with open(r'log\request_log.txt', 'a+') as f:
													f.write("Пользователь " + phonenumber + " Chat ID:" + str(
														message.chat.id) + " User_ID: "
													        + str(user_id) + " Contract_code: " + "%d" % (
														        row[0]) + " запрашивает баланс в "
													        + str(nowDateTime) + '\n')
													f.close()
											except :
												await bot.send_message(124902528, 'Не удалось записать данные в log')
											for row in balance:
												await bot.send_message(message.chat.id, 'Ваш текущий баланс: ' + str(
													round(row[0], 2)) + ' руб.' + '\n')
										except:
											with open(r'log\request_log.txt', 'a+') as f:
												f.write('НЕИЗВЕСТНЫЙ пользователь User_ID: ' + str(
													user_id) + ' Contract_code: ' + '%d' % (
													        row[
														        0]) + ' запрашивает баланс абонента: ' + phonenumber + ' в ' + str(
													nowDateTime) + '\n')
												f.close()
												await bot.send_message(message.chat.id,
												                       'Ошибка получения результата функции f_get_balance или записи в log файл')
										if payments != "Null":
											await bot.send_message(message.chat.id, 'Поступившие платежи:' + '\n')
											for row in payments:
												try:
													await bot.send_message(message.chat.id,
													                       '%s' % (row[0]) + ": " + str(
														                       round(row[1], 2)) + ' руб.')
												except:
													await bot.send_message(124902528,
													                       'сработал Exception в блоке отправки платежей')
										elif payments == 'Null':
											await bot.send_message(message.chat.id, "Платежей не зарегистрировано")
								elif contract_code is not None and contract_code == 50323:
									await bot.send_message(message.chat.id,
									                       'Ваш телефонный номер привязан к л/с организации Связист, вывод данных о балансе отменен.')
								elif contract_code is None:
									await bot.send_message(message.chat.id,
									                       'Номер телефона не найден. Зарегистрируйте его в ' + hlink(
										                       'личном кабинете ', 'https://bill.sv-tel.ru') +
									                       'в разделе "Заявления - Получение уведомлений"', parse_mode='HTML')
								else:
									await bot.send_message(message.chat.id, 'Что-то пошло совсем не так...')
					elif checkPhone_result == "0" or checkPhone_result is None:
						phonenumber = message.contact.phone_number
						f_updateUser(phonenumber, None, message.from_user.id, message.chat.id)
						contract_code = f_contract_code(phonenumber)
						if contract_code is not None:
							f_updateUser(phonenumber, contract_code[0][0], message.from_user.id, message.chat.id)
							await bot.send_message(message.from_user.id,
						                        "Номер сохранен, разрешение на его использование получено.")
							await start(message)
						else:
							await bot.send_message(message.chat.id,
							                       'Номер телефона не найден в биллинговой системе ООО "Связист".'
							                       ' Зарегистрируйте его в ' + '[личном кабинете](https://bill.sv-tel.ru)'
							                       + 'в разделе "Заявления - Получение уведомлений"', parse_mode='Markdown')
			elif checkPhone == 'Null' or checkPhone is None:
				await bot.send_message(message.from_user.id, 'Нажмите /start')
		else:
			await bot.send_message(message.from_user.id, 'Не надо сразу отправлять свой контакт, давайте действовать'
			                                             ' последовательно. Нажмите /start')
			f_addUser(message.from_user.id, message.chat.id)
			f_updateUser(message.contact.phone_number, None, message.from_user.id, message.chat.id)
	else:
		await bot.send_message(message.chat.id, 'Похоже вы пытаетесь запросить баланс другого пользователя.')
		try:
			f = open(r'log\request_log.txt', 'a+')
			f.write("Пользователь " + "User_ID: " + str(message.chat.id) + ' запрашивает чужой баланс в: ' + str(
				nowDateTime) + '\n')
			f.close()
		except:
			print('Что-то пошло не так в блоке обработке лога...')


@dp.message(lambda message: message.text == 'Мои заявки в тех.поддержку')
async def tech_claims(message: types.Message):
	user_id = message.from_user.id
	contract_code = f_isC_Code(str(user_id))
	if contract_code[0] is not None:
		claimslist = f_isTechClaims(contract_code)
		if claimslist is not None:
			await bot.send_message(user_id, 'Ниже выведены заявки в службу технической поддержки за последние 7 дней.',parse_mode='HTML')
			for index in range(len(claimslist)):
				value = claimslist[index]
				await bot.send_message(user_id, 'Номер договора '+ value['CONTRACT'] + '\n'
				                                'Заявка № ' + value['CLAIM_NUM'] + '\n'
				                                'от ' + value['APPL_DATE_CREATE'] + '\n'
				                                'Проблема: ' + value['ERROR_NAME'] + '\n'
				                                'Дополнительное инфо: ' + value['INFO_PROBLEMS_NAME']+ '\n'
				                                'Назначена дата выполнения: ' + value['APPL_DATE_RUN'] + '\n\n'
				                                'Контактные данные по заявке: ' + '\n'
				                                'ФИО: ' + value['CLIENT_NAME'] + '\n'
				                                'Адрес: ' + value['ADDRESS_NAME'] + '\n'
				                                'Контактный телефон: ' + value['PHONE'] + '\n'
				                       )
		elif claimslist is None:
			await bot.send_message(user_id, 'За последнюю неделю не было создано ни одной заявки.\n'
			                                ' Если вы уверены, что это не так, обратитесь в техническую поддержку по'
			                       +'[ телефону +78314577777](tel:+78314577777)', parse_mode='Markdown')
	elif contract_code[0] is None:
		await bot.send_message(user_id, 'Не можем определить ваш номер договора по номеру телефона.'
		                                ' Отправьте нам свой телефон, после чего повторно запросите заявки.')


@dp.message(lambda message: message.text == 'Получить "Доверительный платеж"')
async def setPromisedPay(message: types.Message):
	try:
		contract_code = f_isC_Code(str(message.from_user.id))
		client_code = f_getClientCode(str(contract_code[0]))
		exec_result = f_setPromesedPay(client_code)
		if exec_result is not None:
			RESULT_TEXT = exec_result[0][0]
			if RESULT_TEXT == 'New record. Insert done!' or RESULT_TEXT == 'Existing record. Update Done!':
				await bot.send_message(message.from_user.id, 'Доступ к услугам предоставлен на 3 дня. Активация услуг произойдет не позднее чем через 30 минут.')
			elif RESULT_TEXT == 'Err1: Your IP is not allowed!':
				await bot.send_message(message.from_user.id, 'Сообщите в тех.поддержку код ошибки "Err1"')
			elif RESULT_TEXT == 'Err2: Client Code is null':
				await bot.send_message(message.from_user.id, 'Сообщите в тех.поддержку код ошибки "Err2"')
			elif RESULT_TEXT == 'Err3: Advance Client. Promised pay not allowed!':
				await bot.send_message(message.from_user.id,'Для абонентов с авансовой системой расчетов невозможно установить "доверительный платеж"')
			elif RESULT_TEXT == 'Err4: Too often trying setup properties':
				prop_date = f_getPromisedPayDate(client_code)
				await bot.send_message(message.from_user.id,'С предыдущего запроса "доверительного платежа" прошло менее месяца.\n'
				                                            f' Дата предыдущего "доверительного платежа": {prop_date}')
		else:
			print('Получен пустой exec_result')
			print(exec_result)
	except Exception as e:
		print(f'main error: {e}')
		await bot.send_message(message.from_user.id, 'Не удалось получить доверительный платеж')


# Func list ON
def f_contract_code(phonenumber):
	while True:
		conn = pyodbc.connect(conn_str, autocommit=True)
		try:
			cursor = conn.cursor()
			cursor.execute(getContractCode, phonenumber)
			cc_result = cursor.fetchall()
			cursor.close()
			conn.close()
			if not cc_result:
				return None
			else:
				return cc_result
		except:
			conn = pyodbc.connect(conn_str, autocommit=True)
def f_get_balance(c_code):
	while True:
		conn = pyodbc.connect(conn_str, autocommit=True)
		try:
			cursor = conn.cursor()
			cursor.execute(getBalance, c_code)
			b_result = cursor.fetchall()
			cursor.close()
			conn.close()
			return b_result
		except:
			conn = pyodbc.connect(conn_str, autocommit=True)
def f_get_payments(c_code):
	while True:
		conn = pyodbc.connect(conn_str, autocommit=True)
		try:
			cursor = conn.cursor()
			cursor.execute(getPayments, c_code)
			pay_result = cursor.fetchmany(3)
			cursor.close()
			if not pay_result:
				return 'Null'
			else:
				return pay_result
		except:
			conn = pyodbc.connect(conn_str, autocommit=True)
			conn.close()
def f_get_grant_on_phone(user_id):
	while True:
		try:
			conn = pyodbc.connect(conn_str, autocommit=True)
			cursor = conn.cursor()
			cursor.execute(checkPhone, str(user_id))
			result = cursor.fetchall()
			cursor.close()
			conn.close()
			if not result:
				return 'Null'
			else:
				return result
		except:
			bot.send_message(message.from_user.id, 'Вы вызвали исключение! Как вам это удалось?!')
def f_addUser(user_id, chat_id):
	#while True:
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(addUser, str(user_id), str(chat_id))
		cursor.commit()
		cursor.close()
		conn.close()
		return 'Ok'
	except:
		bot.send_message(124902528, 'Не удалось записать в базу')
		cursor.rollback()
def f_checkUserExists(user_id):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(checkUserExists, str(user_id))
		result = cursor.fetchone()
		cursor.close()
		conn.close()
		if not result:
			return "Null"
		else:
			return result
	except:
		bot.send_message(message.from_user.id, 'Не могу проверить пользователя')
def f_updateUser(phonenumber, contract_code, user_id, chat_id):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(updateUser, str(phonenumber), contract_code, str(user_id), str(chat_id))
		cursor.commit()
		cursor.close()
		conn.close()
	except:
		cursor.rollback()
		bot.send_message(124902528, 'Не могу обновить данные по пользователю')

def f_getLastPayment():
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(getLastPayment)
		columns = [column[0] for column in cursor.description]
		payments_list = []
		for row in cursor.fetchall():
			payments_list.append(dict(zip(columns,row)))
		cursor.close()
		conn.close()
		return payments_list
	except pyodbc.Error as e:
		logging.warning(e)
		return -1

async def f_send_PaymentNotify(wait_for):
	while True:
		await asyncio.sleep(wait_for)
		try:
			payment_list = f_getLastPayment()
			for index in range(len(payment_list)):
				value = payment_list[index]
				isUser_id = value['user_id']
				isPay_money = value['PAY_MONEY']
				logging.debug(index, f'Пользователь {isUser_id} произвел оплату на сумму {isPay_money}')
				await bot.send_message(isUser_id, f'Поступила оплата на сумму {round(isPay_money, 2)} руб.')
				await f_set_SendStatus(1, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), isPay_money,
				                       str(isUser_id))
		except Exception as e:
			print('Тут, это...такое дело. Exception поймали, что с ним делать?')
			print(e)
			return -1

async def f_set_SendStatus(status, time, paid_money,user_id):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(setSendStatus, status, time, paid_money,str(user_id))
		cursor.commit()
		cursor.close()
		conn.close()
	except pyodbc.Error as e:
		cursor.rollback()
		logging.warning(e)
		await bot.send_message(124902528,'Не удалось записать данные по отправке уведомления')

def f_isTechClaims(contract_code):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(getTechClaims, contract_code)
		columns = [column[0] for column in cursor.description]
		claims_list = []
		for row in cursor.fetchall():
			claims_list.append(dict(zip(columns, row)))
		cursor.close()
		conn.close()
		if claims_list is None or len(claims_list) == 0:
			return None
		else:
			return claims_list
	except pyodbc.Error as e:
		logging.warning(e)
		return -1

def f_isC_Code(user_id):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(getContractCodeByUserId, user_id)
		result = cursor.fetchone()
		cursor.close()
		conn.close()
		if not result or len(result) == 0:
			return None
		else:
			return result
	except:
		bot.send_message(message.from_user.id, 'Не могу получить CONTRACT_CODE по user_id')

def f_getClientCode(contract_code):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(getClientCodeByContractCode, contract_code)
		result = cursor.fetchone()
		cursor.close()
		conn.close()
		if not result or len(result) == 0:
			return None
		else:
			return result
	except Exception as e:
		print(f'func error: {e}')

def f_setPromesedPay(client_code):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(f'exec MEDIATE..spMangoSetPromisedPay {client_code[0]}')
		exec_result = cursor.fetchall()
		cursor.close()
		conn.close()
		return exec_result
	except Exception as e:
		print(f'set promised pay error: {e}')

def f_getPromisedPayDate(client_code):
	try:
		conn = pyodbc.connect(conn_str, autocommit=True)
		cursor = conn.cursor()
		cursor.execute(getPromisedPayDate, client_code)
		result = cursor.fetchone()
		cursor.close()
		conn.close()
		return result[0]
	except Exception as e:
		print(e)


# Function list OFF

# Добавим чуточку мозгов(вот бы себе так)
@dp.message(content_types=['text'])
async def text(message):
	user_message = message.text.lower()
	if user_message in ['офис', 'офисы', 'адрес', 'куда ехать']:
		await bot.send_message(message.chat.id, 'Самая актуальная информация всегда доступна по ' +
		                       '[ссылке](https://sv-tel.ru/about/contacts)' + '\n\n' + office_address,
		                       parse_mode='Markdown')
	elif user_message in ['параметры']:
		if admin_ids.get(message.from_user.id) is None:
			await bot.send_message(message.from_user.id, 'Restricted command! Gone!')
		else:
			await bot.send_message(message.chat.id,
		                       'Token: ' + TOKEN + '\n' +
		                       'Channel: ' + CHANNEL_ID + '\n' +
		                       'Sber Token: ' + BANK_TOKEN + '\n' +
		                       SERVER + '\n' +
		                       PORT + '\n' +
		                       USER + '\n' +
		                       PASSW + '\n')
	elif message.text in ['айди', 'ай ди', 'chat id', 'чат']:
		await bot.send_message(message.chat.id, message.chat.id)
	elif user_message in ['оплаты']:
		if admin_ids.get(message.from_user.id) is None:
			await bot.send_message(message.from_user.id, 'Restricted command! Gone!')
		else:
			payment_list = f_getLastPayment()
			for index in range(len(payment_list)):
				value = payment_list[index]
				isUser_id = value['user_id']
				isPay_money = value['PAY_MONEY']
				print(index, f'Пользователь {isUser_id} произвел оплату на сумму {isPay_money}')
				await bot.send_message(isUser_id, f'Поступила оплата на сумму {round(isPay_money, 2)} руб.')
	elif user_message in ['главрыба!']:
		await message.answer(
			'«Абырва́лг» — второе (нередко цитируется как первое) слово, сказанное героем повести Михаила'
			' Булгакова «Собачье сердце» Шариковым после его «оживления» в человеческом облике.'
			' Слово прозвучало также в одноимённом фильме, снятом режиссёром Владимиром Бортко (1988)')

	elif user_message in ['менеджер']:
		if manager_ids.get(message.from_user.id) is None:
			await bot.send_message(message.from_user.id, 'Restricted command! Gone!')
		else:
			await bot.send_message(message.from_user.id, 'Менеджеры(права на большую часть команд):')
			for value in manager_ids:
				await bot.send_message(message.from_user.id, f'user: {value}')
	elif user_message in ['админ']:
		if admin_ids.get(message.from_user.id) is None:
			await bot.send_message(message.from_user.id, 'Restricted command! Gone!')
		else:
			await bot.send_message(message.from_user.id, 'Админы(права на все команды):')
			for value in admin_ids:
				await bot.send_message(message.from_user.id, f'user: {value}')
	elif user_message in ['my message']:
		await bot.send_message(message.from_user.id, f'{message}')
	elif user_message in ['stop']:
		if admin_ids.get(message.from_user.id) is None:
			await bot.send_message(message.from_user.id, 'Restricted command! Gone!')
		else:
			bot.close()
	else:
		await message.answer('!АБЫРВАЛГ')


@dp.message(content_types=['audio'])
async def audio(message):
	await message.reply('''Let's Music!!!''')


@dp.message(content_types=['photo'])
async def photo(message):
	await message.reply('красиво')


@dp.message(content_types=['voice'])
async def voice(message):
	await message.reply("Я не умею в войсы")


@dp.message(content_types=['location'])
async def location(message):
	await message.reply('к сожалению не могу посетить это место')


@dp.message(content_types=['document'])
async def document(message):
	await message.reply('Документ')

async def telegram_bot_app():
	try:
		print('Устанавливаю подключение к БД Sybase')
		pyodbc.connect(conn_str, autocommit=True)
		loop = asyncio.get_event_loop()
		loop.create_task(f_send_PaymentNotify(61))
		# loop.create_task(f_send_ClaimNotify(61))
		print('Подключение установлено.')
		print('Запускаю основное тело программы')
		await dp.start_polling(bot, skip_updates=False)
	finally:
		await bot.close()


if __name__ == "__main__":
	print('Запуск программы')
	asyncio.run(telegram_bot_app())
