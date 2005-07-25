#-----------------------------------------------------------------------------
# Name:        wxDialogUtils.py
# Product:     ClamWin Free Antivirus
#
# Author:      alch [alch at users dot sourceforge dot net]
#
# Created:     2004/08/05
# Copyright:   Copyright alch (c) 2004
# Licence:     
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

#-----------------------------------------------------------------------------

import os, sys, tempfile, time, re
import wxDialogStatus, wxDialogPreferences, wxDialogAbout
import wxDialogLogViewer
from wxPython.wx import wxBitmap, wxTextCtrl
from wxPython.lib.dialogs import wxScrolledMessageDialog
import MsgBox, EmailAlert, Utils


def wxUpdateVirDB(parent, config, autoClose = False):        
    exit_code = -1
    freshclam_conf = Utils.SaveFreshClamConf(config)
    if not len(freshclam_conf):
        MsgBox.ErrorBox(parent, 'Unable to cerate freshclam configutration file. Please check there is enough space on the disk')
        return
    updatelog = tempfile.mktemp()       
    dbdir = config.Get('ClamAV', 'Database')
    # create database folder before downloading
    if not os.path.exists(dbdir):
        try:
            os.makedirs(dbdir)
        except:
            pass
    cmd = '--stdout --datadir="' + dbdir.replace('\\', '/') + '"' + \
          ' --config-file="%s" --log="%s"' % (freshclam_conf, updatelog)
    cmd = re.sub('([A-Za-z]):[/\\\\]', r'/cygdrive/\1/', cmd).replace('\\', '/')
    if config.Get('ClamAV', 'Debug') == '1':
        cmd += ' --debug'    
    cmd = '"%s" %s' % (config.Get('ClamAV', 'FreshClam'), cmd)
    if sys.platform.startswith('win') and config.Get('UI', 'TrayNotify') == '1':        
        import win32gui
        tray_notify_params = (('Virus Database has been updated.', 0, 
                           win32gui.NIIF_INFO, 10000),
                           ('An error occured during Virus Database Update. Please review the update report.', 1, 
                           win32gui.NIIF_WARNING, 30000)
                           )
    else:
        tray_notify_params = None

    dlg = wxDialogStatus.create(parent, cmd, None, 'n', 'update', tray_notify_params)
    dlg.SetTitle('ClamWin Internet Update Status')
    dlg.SetAutoClose(autoClose)
    try:
        dlg.ShowModal()
        exit_code = dlg.GetExitCode()
        Utils.SetDbFilesPermissions(config.Get('ClamAV', 'Database'))
        maxsize = int(config.Get('ClamAV', 'MaxLogSize'))*1048576        
        logfile = config.Get('Updates', 'DBUpdateLogFile')
        Utils.AppendLogFile(logfile, updatelog, maxsize)       
    finally:
        try:
            os.remove(updatelog)
        except Exception, e:
            print 'Unable to remove file %s. Error: %s' % (updatelog, str(e))
        dlg.Destroy()         
        try:
            os.remove(freshclam_conf)        
        except Exception, e:
            print "couldn't remove file %s. Error: %s" % (freshclam_conf, str(e))        
        if exit_code == 1:
            try:
                f = file(os.path.join(tempfile.gettempdir(), 'ClamWin_Upadte_Time'), 'w')
                f.write(str(time.time()))
                f.close()                       
            except IOError:
                pass
        return exit_code
    
def wxScan(parent, config, path, autoClose = False):            
    exit_code = -1
    scanlog = tempfile.mktemp()    
    cmd = Utils.GetScanCmd(config, path, scanlog)
    try:
        priority = config.Get('ClamAV', 'Priority')[:1].lower()
    except:
        priority = 'n'      
    if sys.platform.startswith('win') and config.Get('UI', 'TrayNotify') == '1':
        import win32gui
        tray_notify_params = (('Virus has been detected during scan! Please review the scan report.', 1, 
                        win32gui.NIIF_ERROR, 30000),
                        ('An error occured during virus scan. Please review the scan report.', 0, 
                        win32gui.NIIF_WARNING, 30000))      
    else:
        tray_notify_params = None
    dlg = wxDialogStatus.create(parent, cmd, scanlog, priority, "scanprogress", tray_notify_params)
    dlg.SetTitle("ClamWin Scan Status")
    dlg.SetAutoClose(autoClose, 0)
    try:
        dlg.ShowModal()         
        exit_code = dlg.GetExitCode()                
        maxsize = int(config.Get('ClamAV', 'MaxLogSize'))*1048576        
        logfile = config.Get('ClamAV', 'LogFile')
        Utils.AppendLogFile(logfile, scanlog, maxsize)        
        # send email alert
        if config.Get('EmailAlerts', 'Enable') == '1':            
            try:     
                # unix version returns 256 on virus detection
                # strange but maybe it is cygwin the culprit?
                if exit_code == 1 or exit_code ==256:
                    msg = EmailAlert.ConfigVirusAlertMsg(config, (scanlog,))
                    msg.Send()                
            except Exception, e:
                print 'Could not send email alert. Error: %s' % str(e)
              
    finally:
        if os.path.exists(scanlog):
             try:
                 os.remove(scanlog)
             except IOError, e:
                 print 'could not delete logfile : %s. Error: %s' % (scanlog, str(e))                 
        dlg.Destroy()
        return exit_code


def wxConfigure(parent, config, switchToSchedule = False):
    dlg = wxDialogPreferences.create(parent, config, switchToSchedule)
    try:
        dlg.ShowModal()
    finally:
        dlg.Destroy()            

def wxAbout(parent, config):
    dlg = wxDialogAbout.create(parent, config)
    try:
        dlg.ShowModal()
    finally:
        dlg.Destroy()       

def wxShowLog(parent, logfile):
        maxlogsize = 524288 #512 KB        
        if not len(logfile):
            MsgBox.ErrorBox(parent, 'Log files are not properly configured. Please review ClamWin configuration')        
        try:                        
            if not os.path.isfile(logfile):
                text = ''
            else:
                if os.stat(logfile).st_size > maxlogsize:                    
                    # read last 512 kbytes from the file
                    f = file(logfile, 'rt')
                    f.seek(-maxlogsize, 2)
                    text = f.read()                    
                else:
                    text = file(logfile, 'rt').read()                                    
        except Exception, e:
            MsgBox.ErrorBox(parent, 'Unable to read from the log file. Error: %s' % str(e))
            
        dlg = wxDialogLogViewer.create(parent, text, True)        
        try:
            # change window title to include the file we are viewing
            dlg.SetTitle(dlg.GetTitle() + ' - ' + os.path.split(logfile)[1])
            dlg.ShowModal()
        finally:
            dlg.Destroy()
            
def wxGoToInternetUrl(url):
    try:
        import webbrowser
    except ImportError:
        wxMessageBox('Please point your browser at: %s' % url)
    else:
        webbrowser.open(url)