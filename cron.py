#!/usr/bin/env python

import datetime
import os

import crython
from mailboxclient import Exporter

cron_expr = os.getenv('IMAPBOX_CRON_EXPR', '@hourly')


@crython.job(expr=cron_expr)
def cronjob():
    print("__Job__started: " + str(datetime.datetime.now()))
    Exporter().run()
    print("__Job_finished: " + str(datetime.datetime.now()))


print('_crython_start: ' + str(datetime.datetime.now()) + " " + cron_expr)
crython.start()
crython.join()
