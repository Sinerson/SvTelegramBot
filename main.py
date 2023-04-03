import re
import asyncio
import datetime
import logging

import pyodbc
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.markdown import link

import config
# Импортируем настройки
from config import DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, \
	APPLICATION_NAME, TOKEN
from func import f_contract_code, f_get_balance, f_get_payments, f_get_grant_on_phone, f_addUser, f_checkUserExists, \
	f_updateUser, f_getLastPayment, f_send_PaymentNotify, f_isTechClaims, isC_Code, setPromesedPay, getClientCode
# Импортируем адреса офисов и режим работы
from office import office_address

# Включим логирование
logging.basicConfig(level=logging.DEBUG, filename="DEBUG_log.log", filemode="a")

# Отдадим боту его токен
bot = Bot(config.TOKEN)  # Для aiogram
dp = Dispatcher()

# Объявим строку подключения к БД
conn_str = ';'.join([DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, APPLICATION_NAME])


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
			button_phone = [[type.KeyboardButton(text="Отправить контакт и узнать баланс", request_contact=True)]]
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
	if message.contact is not None and message.contact.user_id == message.chat.id \
			or message.from_user.id == 124902528 or message.from_user.id == 1345730215:
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
							                       ' Зарегистрируйте его в ' + link('личном кабинете',
							                                                        'https://bill.sv-tel.ru') +
							                       'в разделе "Заявления - Получение уведомлений"')
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
											except:
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
									                       'Номер телефона не найден. Зарегистрируйте его в ' + link(
										                       'личном кабинете', 'https://bill.sv-tel.ru') +
									                       'в разделе "Заявления - Получение уведомлений"')
								else:
									await bot.send_message(message.chat.id, 'Что-то пошло совсем не так...')
					elif checkPhone_result == "0" or checkPhone_result is None:
						phonenumber = message.contact.phone_number
						f_updateUser(phonenumber, None, message.from_user.id, message.chat.id)
						await bot.send_message(message.from_user.id,
						                       "Номер сохранен, но нет разрешения на его добавление в базу нажмите /start если согласны...")
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
	contract_code = isC_Code(str(user_id))
	if contract_code[0] is not None:
		claimslist = f_isTechClaims(contract_code)
		if claimslist is not None:
			await bot.send_message(user_id, 'Ниже выведены заявки в службу технической поддержки за последние 7 дней.')
			#print(claimslist)
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
			                                'Если вы уверены, что это не так, обратитесь в техническую поддержку по телефону +78314577777'
			                       )
	elif contract_code[0] is None:
		await bot.send_message(user_id, 'Не можем определить ваш номер договора по номеру телефона.'
		                                ' Отправьте нам свой телефон, после чего повторно запросите заявки.')


@dp.message(lambda message: message.text == 'Получить "Доверительный платеж"')
async def setPromisedPay(message: types.Message):
	try:
		contract_code = isC_Code(str(message.from_user.id))
		client_code = getClientCode(str(contract_code[0]))
		exec_result = setPromesedPay(client_code)
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
				await bot.send_message(message.from_user.id,'Вы уже запрашивали доверительный платеж менее месяца назад. Попробуйте позднее.')
		else:
			print('Получен пустой exec_result')
			print(exec_result)
	except Exception as e:
		print(f'main error: {e}')
		await bot.send_message(message.from_user.id, 'Не удалось получить доверительный платеж')


# Func list ON
# Функции вынесены в отдельный файл func.py
# Function list OFF

# Добавим чуточку мозгов(вот бы себе так)
@dp.message(content_types=['text'])
async def text(message):
	user_message = message.text.lower()
	if user_message in ['офис', 'офисы', 'адрес', 'куда ехать']:
		await bot.send_message(message.chat.id, 'Самая актуальная информация всегда доступна по ' +
		                       '[ссылке](https://sv-tel.ru/about/contacts)' + '\n\n' + office_address,
		                       parse_mode='Markdown')
	elif message.from_user.id == 124902528 and user_message in ['параметры']:
		await bot.send_message(message.chat.id,
		                       'Token: ' + token + '\n' +
		                       'Channel: ' + channel_id + '\n' +
		                       'Sber Token: ' + SberToken + '\n' +
		                       server + '\n' +
		                       port + '\n' +
		                       user + '\n' +
		                       pw + '\n')
	elif message.text in ['айди', 'ай ди', 'chat id', 'чат']:
		await bot.send_message(message.chat.id, message.chat.id)
	elif message.from_user.id == 124902528 and user_message in ['оплаты']:
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
	conn = pyodbc.connect(conn_str)
	loop = asyncio.get_event_loop()
	loop.create_task(f_send_PaymentNotify(61))
	# loop.create_task(f_send_ClaimNotify(61))
	await dp.start_polling(bot)


if __name__ == "__main__":
	asyncio.run(telegram_bot_app())
