import asyncio
import os


def start():
	from main import bot_app
	asyncio.run(bot_app())

WINSERVICE = False

try:
	if os.name == 'nt':
		import win32serviceutil
		import win32service
		import servicemanager
		WINSERVICE = True
except:
	pass

if WINSERVICE:
	class AppServerSvc(win32serviceutil.ServiceFramework):
		_svc_name_ = "Telegram Bot"
		_svc_display_name_ = "Telegram Bot"

		def __init__(self, args):
			import multiprocessing as mp
			win32serviceutil.ServiceFramework.__init__(self, args)
			self.proc = mp.Process(target=start)

		def SvcStop(self):
			self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
			self.proc.terminate()

		def SvcDoRun(self):
			servicemanager.LogMsg(
									servicemanager.EVENTLOG_INFORMATION_TYPE,
			                        servicemanager.PYS_SERVICE_STARTED,(self._svc_name_,'')
			                      )
			try:
				self.proc.start()
				self.proc.join()
			except Exception as e:
				import traceback
				import sys
				exc_type, exc_value, exc_traceback = sys.exc_info()
				servicemanager.LogMsg   (
										servicemanager.EVENTLOG_INFORMATION_TYPE,
										0xF000,
										(
											self._svc_name_,"\n".join(traceback.format_tb(exc_traceback))
										)
										)
def entry_point():
	if WINSERVICE:
		win32serviceutil.HandleCommandLine(AppServerSvc)
	else:
		start()
if __name__ == "__main__":
	entry_point()