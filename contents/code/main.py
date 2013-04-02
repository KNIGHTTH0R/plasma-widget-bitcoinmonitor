#!/usr/bin/env python

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.plasma import Plasma
from PyKDE4 import plasmascript,kdecore,kio
from json import load, loads
from urllib2 import urlopen,URLError,build_opener,HTTPCookieProcessor
from time import time,localtime

url = ["http://deepbit.net/api/", \
       "http://www.btcguild.com/api.php?api_key=", \
       "https://mining.bitcoin.cz/accounts/profile/json/", \
       "http://btcmine.com/api/getbalance/", \
       "http://www.bitcoinpool.com/user.php?u=", \
       "https://mineco.in/users/", \
       "https://mtred.com/api/user/key/", \
       "https://arsbitcoin.com/api.php?api_key=", \
       "https://50btc.com/api/"]
url2 = ["", "", "", "", "&json=1", ".json","","",""]

class bitcoinmonitorApplet(plasmascript.Applet):
    def __init__(self,parent,args = None):
        plasmascript.Applet.__init__(self,parent)
        self.last_getrate = 0
        self.update_interval = 300 #5 minutes

    def init(self):
        self.setAspectRatioMode(Plasma.IgnoreAspectRatio)
        self.setHasConfigurationInterface(True)
        self.dialog = None
        cg = self.config()
        self.APIkey = cg.readEntry("APIkey", QString("")).toString()
        self.pool = cg.readEntry("pool", 0).toInt()[0]
        self.mainvalue = cg.readEntry("mainvalue", 0).toInt()[0]

        self.layout = QGraphicsLinearLayout(Qt.Horizontal, self.applet)
        self.applet.setLayout(self.layout)
        self.label = Plasma.Label(self.applet)
        self.label.setAlignment(Qt.AlignVCenter)

        svg = Plasma.Svg(self)
        icon_path = self.package().path() + "contents/icons/logo.svg"
        svg.setImagePath(icon_path)
        self.ttip_icon = QIcon(icon_path)
        self.icon = Plasma.SvgWidget(svg)
        self.icon.setPreferredSize(20,20)
        policy = QSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.icon.setSizePolicy(policy)

        self.layout.addItem(self.icon)
        self.layout.setAlignment(self.icon,Qt.AlignCenter)
        self.layout.addItem(self.label)

        if self.APIkey != "":
            self.update_data()
        self.update()
        self.startTimer(30000) #30 seconds

    def showConfigurationInterface(self):
        windowTitle = str(self.applet.name()) + " Settings" #i18nc("@title:window", "%s Settings" % str(self.applet.name()))
        self.ui = uic.loadUi(self.package().filePath('ui', '../ui/settings_general.ui'), self.dialog)

        if self.dialog is None:
            self.dialog = KDialog(None)
            self.dialog.setWindowTitle(windowTitle)
            self.dialog.setMainWidget(self.ui)
            self.dialog.setButtons(KDialog.ButtonCodes(KDialog.ButtonCode(KDialog.Ok | KDialog.Cancel)))

            self.connect(self.dialog, SIGNAL("applyClicked()"), self, SLOT("configAccepted()"))
            self.connect(self.dialog, SIGNAL("okClicked()"), self, SLOT("configAccepted()"))

        self.ui.APIkey.setText(self.APIkey)
        self.ui.pool.setCurrentIndex (self.pool)
        self.ui.mainvalue.setCurrentIndex (self.mainvalue)

        self.dialog.show()
    @pyqtSignature("configAccepted()")
    def configAccepted(self):
        cg = self.config()
        self.APIkey = self.ui.APIkey.text()
        self.pool = self.ui.pool.currentIndex()
        self.mainvalue = self.ui.mainvalue.currentIndex()
        cg.writeEntry("APIkey", self.APIkey)
        cg.writeEntry("pool", self.pool)
        cg.writeEntry("mainvalue", self.mainvalue)
        self.update()
        self.emit(SIGNAL("configNeedsSaving()"))
        self.update_data()

    def timerEvent(self,event):
        if time() - self.last_getrate > self.update_interval:
            self.update_data()
        self.update()
    def setToolTip(self):
        last = localtime(self.last_getrate)
        ttip = Plasma.ToolTipContent()
        ttip.setMainText("Bitcoin monitor")
        if self.pool == 0:
            ttip.setSubText("<br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{1:.1f}</span> MHash/s"\
                .format(self.confirmed, self.hashrate))
        if self.pool == 1:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC\
                <br />Estimated rewards: <span style=\"color:red; font-weight: bold\">{3:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{4:.1f}</span> MHash/s"\
                .format(self.total, self.confirmed, self.unconfirmed, self.estimated, self.hashrate))
        if self.pool == 2:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC\
                <br />Estimated rewards: <span style=\"color:red; font-weight: bold\">{3:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{4:.1f}</span> MHash/s"\
                .format(self.total, self.confirmed, self.unconfirmed, self.estimated, self.hashrate))
        if self.pool == 3:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC"\
                .format(self.total, self.confirmed, self.unconfirmed))
        if self.pool == 4:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC\
                <br />Estimated rewards: <span style=\"color:red; font-weight: bold\">{3:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{4:.1f}</span> MHash/s"\
                .format(self.total, self.confirmed, self.unconfirmed, self.estimated, self.hashrate))
        if self.pool == 5:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC\
                <br />Estimated rewards: <span style=\"color:red; font-weight: bold\">{3:.4f}</span> BTC"\
                .format(self.total, self.confirmed, self.unconfirmed, self.estimated, self.hashrate))
        if self.pool == 6:
            ttip.setSubText("<br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Estimated rewards: <span style=\"color:red; font-weight: bold\">{1:.4f}</span> BTC"\
                .format(self.confirmed, self.estimated))
        if self.pool == 7:
            ttip.setSubText("<br />Total rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Confirmed rewards: <span style=\"color:green; font-weight: bold\">{1:.4f}</span> BTC\
                <br />Unconfirmed rewards: <span style=\"color:orange; font-weight: bold\">{2:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{3:.1f}</span> MHash/s"\
                .format(self.total, self.confirmed, self.unconfirmed, self.hashrate))
        if self.pool == 8:
            ttip.setSubText("<br />Rewards: <span style=\"color:green; font-weight: bold\">{0:.4f}</span> BTC\
                <br />Hashrate: <span style=\"color:blue; font-weight: bold\">{1:.1f}</span> MHash/s"\
                .format(self.confirmed, self.hashrate))
        ttip.setAutohide(False)
        ttip.setImage(self.ttip_icon)
        Plasma.ToolTipManager.self().setContent(self.applet,ttip)
    @pyqtSignature("update_data()")
    def update_data(self):
        self.data_url = kdecore.KUrl(url[self.pool] + str(self.APIkey) + url2[self.pool])
        job = kio.KIO.storedGet(self.data_url, kio.KIO.NoReload, kio.KIO.HideProgressInfo)
        job.result.connect(self.update_values)
    def update_values(self,job):
        if job.error():
            print "job error"
            return
        self.data = loads(str(job.data()))
        self.last_getrate = time()
        self.hashrate = 0
        self.unconfirmed = 0
        if self.pool == 0:
            self.confirmed = float(self.data["confirmed_reward"])
            self.hashrate = float(self.data["hashrate"])
            self.estimated = 0
            self.unconfirmed = 0
        if self.pool == 1:
            self.confirmed = float(self.data["user"]["confirmed_rewards"])
            self.unconfirmed = float(self.data["user"]["unconfirmed_rewards"])
            self.estimated = float(self.data["user"]["estimated_rewards"])
            for worker in self.data["workers"]:
                self.hashrate += float(self.data["workers"][worker]["hash_rate"])
        if self.pool == 2:
            self.confirmed = float(self.data["confirmed_reward"])
            self.unconfirmed = float(self.data["unconfirmed_reward"])
            self.estimated = float(self.data["estimated_reward"])
            self.hashrate = 0
            for worker in self.data["workers"]:
                self.hashrate += float(self.data["workers"][worker]["hashrate"])
        if self.pool == 3:
            self.confirmed = float(self.data["confirmed"])
            self.unconfirmed = float(self.data["unconfirmed"])
            self.estimated = 0
            self.hashrate = 0
        if self.pool == 4:
            self.confirmed = float(self.data["User"]["unpaid"])
            self.unconfirmed = float(self.data["User"]["unconfirmed"])
            self.estimated = float(self.data["User"]["estimated"])
            self.hashrate = float(self.data["User"]["currSpeed"].replace(' MH/s', ''))
        if self.pool == 5:
            self.confirmed = float(self.data["user"]["confirmed_reward"])
            self.unconfirmed = float(self.data["user"]["unconfirmed_reward"])
            self.estimated = float(self.data["user"]["estimated_reward_this_round"])
            self.hashrate = 0
        if self.pool == 6:
            self.confirmed = float(self.data["balance"])
            self.unconfirmed = 0
            if float(self.data["server"]["roundshares"]) != 0:
                self.estimated = float(self.data["rsolved"]) / float(self.data["server"]["roundshares"]) * 50
            else:
                self.estimated = 0
            self.hashrate = 0
        if self.pool == 7:
            self.confirmed = float(self.data["confirmed_rewards"])
            self.unconfirmed = float(self.data["totalPPSWork"])-float(self.data["paidPPSWork"])
            self.estimated = 0
            self.hashrate = float(self.data["hashrate"])
        if self.pool == 8:
            self.confirmed = float(self.data["user"]["confirmed_rewards"])
            self.unconfirmed = 0
            self.estimated = 0
            self.hashrate = float(self.data["user"]["hash_rate"])
        self.total = self.confirmed + self.unconfirmed
        if self.mainvalue == 0:
            self.label.setText("{0:.4f}".format(self.total))
        if self.mainvalue == 1:
            self.label.setText("{0:.4f}".format(self.confirmed))
        if self.mainvalue == 2:
            self.label.setText("{0:.4f}".format(self.unconfirmed))
        if self.mainvalue == 3:
            self.label.setText("{0:.4f}".format(self.estimated))
        if self.mainvalue == 4:
            self.label.setText("{0:.1f}".format(self.hashrate))
        self.setToolTip()
        self.adjustSize()
        return True

def CreateApplet(parent):
    return bitcoinmonitorApplet(parent)
