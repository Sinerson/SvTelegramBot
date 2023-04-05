# импортируем библиотеки аснихронности и работы с БД
import logging
import datetime
from aiogram import Bot

import config

bot = Bot(config.TOKEN)

import pyodbc, asyncio
# импортируем запросы
from sql import checkPhone, checkUserExists, addUser, updateUser, getContractCode, getBalance, getPayments, \
	getLastPayment, setSendStatus, getTechClaims, getContractCodeByUserId, getClientCodeByContractCode
# импортируем настройки
from config import DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, \
	APPLICATION_NAME
# строка подключения к БД
conn_str = ';'.join([DRIVER, SERVER, PORT, USER, PASSW, LANGUAGE, CLIENT_HOST_NAME, CLIENT_HOST_PROC, APPLICATION_NAME])

def f_contract_code(phonenumber):
	while True:
		conn = pyodbc.connect(conn_str)
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
			conn = pyodbc.connect(conn_str)
def f_get_balance(c_code):
	while True:
		conn = pyodbc.connect(conn_str)
		try:
			cursor = conn.cursor()
			cursor.execute(getBalance, c_code)
			b_result = cursor.fetchall()
			cursor.close()
			conn.close()
			return b_result
		except:
			conn = pyodbc.connect(conn_str)
def f_get_payments(c_code):
	while True:
		conn = pyodbc.connect(conn_str)
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
			conn = pyodbc.connect(conn_str)
			conn.close()
def f_get_grant_on_phone(user_id):
	while True:
		try:
			conn = pyodbc.connect(conn_str)
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
			bot.send_message(message.chat.id, 'Вы вызвали исключение! Как вам это удалось?!')
def f_addUser(user_id, chat_id):
	#while True:
	try:
		conn = pyodbc.connect(conn_str)
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
		conn = pyodbc.connect(conn_str)
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
		conn = pyodbc.connect(conn_str)
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
		conn = pyodbc.connect(conn_str)
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

#
#async def f_send_ClaimNotify(wait_for):
#	while True:
#		await asyncio.sleep(wait_for)
#		try:
#

async def f_set_SendStatus(status, time, paid_money,user_id):
	try:
		conn = pyodbc.connect(conn_str)
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
		conn = pyodbc.connect(conn_str)
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

def isC_Code(user_id):
	try:
		conn = pyodbc.connect(conn_str)
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

def getClientCode(contract_code):
	try:
		conn = pyodbc.connect(conn_str)
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

def setPromesedPay(client_code):
	try:
		conn = pyodbc.connect(conn_str)
		cursor = conn.cursor()
		cursor.execute('SET CHAINED OFF')
		cursor.execute(f'exec MEDIATE..spMangoSetPromisedPay {client_code[0]}')
		exec_result = cursor.fetchall()
		cursor.execute('SET CHAINED ON')
		cursor.close()
		conn.close()
		return exec_result
	except Exception as e:
		print(f'set promised pay error: {e}')
