# SQL queries
checkPhone = """select grant_phone
               from SV..TBP_TELEGRAM_BOT
			   where chat_id = (?)
			"""
checkUserExists = """select E = case
					when exists(
					select    phonenumber
					from    SV..TBP_TELEGRAM_BOT
					where     user_id = (?)
					)
					then 1
					else 0
					end"""

addUser = """insert into SV..TBP_TELEGRAM_BOT (user_id, chat_id, date)
					values ((?),(?),getdate())"""

updateUser = """update SV..TBP_TELEGRAM_BOT
					set phonenumber = (?),
                    grant_phone = '1',
                    contract_code = cast((?) as int)
					where user_id = (?) and chat_id = (?)"""

delPhone = """update SV..TBP_TELEGRAM_BOT
					set grant_phone = '0'
					where phonenumber = (?)"""

delUser = """delete from SV.dbo.TBP_TELEGRAM_BOT where chat_id = (?)"""

getContractCode = \
	"""
					select cast(CL.CONTRACT_CODE as numeric(10,0)), cast(CS.CONTRACT as numeric(10,0))
					from INTEGRAL..OTHER_DEVICES OD
					join INTEGRAL..CONTRACT_CLIENTS CL on CL.CLIENT_CODE = OD.CLIENT_CODE
					join INTEGRAL..CONTRACTS CS on CS.CONTRACT_CODE = CL.CONTRACT_CODE
					where DEVICE like '%'+right(cast((?) as varchar), 10)+'%'
"""

getBalance = \
	"""
					declare     @CurDate datetime,
                                @CurMonth datetime
                    select      @CurDate = getdate()
                    select      @CurMonth = M.MONTH
                        from    INT_PAYM..MONTH M
                    where       @CurDate >= M.MONTH and
                                MONTH_NEXT > M.MONTH
                    select      sum(EO_MONEY) as EO_MONEY
                        from    INT_PAYM..CONTRACT_STATE
                    where       MONTH = dateadd(mm,0,@CurMonth) and
                                CONTRACT_CODE = (?)
                    group by    CONTRACT_CODE
"""

getPayments = \
	"""
					declare     @CurDate datetime,
					            @CurMonth datetime
					select      @CurDate = getdate()
					select      @CurMonth = M.MONTH
					    from    INT_PAYM..MONTH M
					where       @CurDate >= M.MONTH and
					            MONTH_NEXT > M.MONTH
					select case
					            when datepart(mm,MONTH) = 1 then 'Январь' when datepart(mm,MONTH) = 2 then 'Февраль'
					            when datepart(mm,MONTH) = 3 then 'Март' when datepart(mm,MONTH) = 4 then 'Апрель'
					            when datepart(mm,MONTH) = 5 then 'Май' when datepart(mm,MONTH) = 6 then 'Июнь'
					            when datepart(mm,MONTH) = 7 then 'Июль' when datepart(mm,MONTH) = 8 then 'Август'
					            when datepart(mm,MONTH) = 9 then 'Сентябрь' when datepart(mm,MONTH) = 10 then 'Октябрь'
					            when datepart(mm,MONTH) = 11 then 'Ноябрь' when datepart(mm,MONTH) = 12 then 'Декабрь'
					        end,
					            sum(PAY_MONEY)
					    from    INT_PAYM..CONTRACT_PAYS
					where       MONTH >= dateadd(mm, -3, @CurDate) and
					            CONTRACT_CODE = (?) and
					            USED = 1
					group by    MONTH
					order by    datepart(mm,MONTH)
"""
getLastPayment = \
	"""
					select user_id, sum(PAY_MONEY) as PAY_MONEY
					from INT_PAYM..CONTRACT_PAYS CP
					join SV..TBP_TELEGRAM_BOT B on CP.CONTRACT_CODE = B.contract_code
					where PAY_DATE >= dateadd(ss,-120, getdate()) and USED = 1
					group by user_id, USED
"""
setSendStatus = \
	"""
					update SV..TBP_TELEGRAM_BOT
					set send_status = (?), send_time = (?), paid_money = (?)
					from SV..TBP_TELEGRAM_BOT
					where user_id = (?)
"""
getTechClaims = \
	"""
					declare @ContractCode int
					select @ContractCode = (?)
					select  A.APPL_ID as CLAIM_NUM,
					        rtrim(S.STATUS_NAME) as STATUS_NAME,
					        cast(A.APPL_DATE_CREATE as smalldatetime) as APPL_DATE_CREATE, -- Дата создания
					        A.APPL_DATE_RUN, -- Дата выполнения
					        B.CONTRACT_ID as CONTRACT,
					        CS.CONTRACT_CODE,
					        rtrim(C.ABON_NAME) as CLIENT_NAME,
					        rtrim(C.ABON_PHONE) as PHONE,
					        rtrim(D.ADDRESS_ABON_NAME) as ADDRESS_NAME,
					        rtrim(E.ERRORS_NAME) as ERROR_NAME,
					        rtrim(IP.INFO_PROBLEMS_NAME) as INFO_PROBLEMS_NAME
					from    SV..TIA_APPLICATION A
					        join SV..TIA_ABON C on A.APPL_ID = C.ABON_ID
					        join SV..TIA_INFO I on A.APPL_INFO_ID = I.INFO_ID
					        left join SV..TIA_STATUS S on A.APPL_STATUS_ID = S.STATUS_ID
					        left join SV..TIA_CONTRACT B on A.APPL_ID = B.CONTRACT_ABON_ID
					        left join SV..TIA_ADDRESS D on A.APPL_ID = D.ADDRESS_ABON_ID
					        left join SV..TIA_INFO_PROBLEMS IP on A.APPL_INFO_PROBLEMS_ID = IP.INFO_PROBLEMS_ID
					        left join SV..TIA_ERRORS E on A.APPL_ERRORS_ID = E.ERRORS_ID
					        join INTEGRAL..CONTRACTS CS on B.CONTRACT_ID = cast(CS.CONTRACT as int)
					where   A.APPL_DATE_CREATE >= dateadd(dd, -7, getdate()) and
					        CS.CONTRACT_CODE = @ContractCode and
					        A.APPL_DATE_CLOSE is null
"""

getContractCodeByUserId = \
	"""
					select contract_code
					from SV..TBP_TELEGRAM_BOT
					where user_id = (?)
"""

getLastTechClaims = \
	"""
					select  A.APPL_ID as CLAIM_NUM,
					rtrim(S.STATUS_NAME) as STATUS_NAME,
					cast(A.APPL_DATE_CREATE as smalldatetime) as APPL_DATE_CREATE, -- Дата создания
					A.APPL_DATE_RUN, -- Дата выполнения
					B.CONTRACT_ID as CONTRACT,
					CS.CONTRACT_CODE,
					rtrim(C.ABON_NAME) as CLIENT_NAME,
					rtrim(C.ABON_PHONE) as PHONE,
					rtrim(D.ADDRESS_ABON_NAME) as ADDRESS_NAME,
					rtrim(E.ERRORS_NAME) as ERROR_NAME,
					rtrim(IP.INFO_PROBLEMS_NAME) as INFO_PROBLEMS_NAME
					from    SV..TIA_APPLICATION A
					join SV..TIA_ABON C on A.APPL_ID = C.ABON_ID
					join SV..TIA_INFO I on A.APPL_INFO_ID = I.INFO_ID
					left join SV..TIA_STATUS S on A.APPL_STATUS_ID = S.STATUS_ID
					left join SV..TIA_CONTRACT B on A.APPL_ID = B.CONTRACT_ABON_ID
					left join SV..TIA_ADDRESS D on A.APPL_ID = D.ADDRESS_ABON_ID
					left join SV..TIA_INFO_PROBLEMS IP on A.APPL_INFO_PROBLEMS_ID = IP.INFO_PROBLEMS_ID
					left join SV..TIA_ERRORS E on A.APPL_ERRORS_ID = E.ERRORS_ID
					join INTEGRAL..CONTRACTS CS on B.CONTRACT_ID = cast(CS.CONTRACT as int)
					join SV..TBP_TELEGRAM_BOT TTB on CS.CONTRACT_CODE = TTB.contract_code
					where   A.APPL_DATE_CREATE >= dateadd(ss, -120, getdate()) and
					        A.APPL_DATE_CLOSE is null
"""
getClientCodeByContractCode = \
	"""
					select CL.CLIENT_CODE, CL.TYPE_CODE
					from INTEGRAL..CONTRACT_CLIENTS CCL
					join INTEGRAL..CLIENTS CL on CCL.CLIENT_CODE = CL.CLIENT_CODE
					where cast(CONTRACT_CODE as varchar(10)) = (?)
"""

getPromisedPayDate = \
	"""
					select cast(DATE_CHANGE as smalldatetime) as DATE_CHANGE
					from INTEGRAL..CLIENT_PROPERTIES
					where CLIENT_CODE = (?) and PROP_CODE = 823
"""
