#!/usr/bin/python
# -*- coding: utf-8 -*-

from Tkinter import *
import Tkinter
import tkMessageBox
import thread
import webbrowser
from tkFileDialog import askdirectory
from bs4 import BeautifulSoup
import os
import requests
import urllib2
import datetime
import base64
import string
import getpass
import multiprocessing
import functools
from io import open as iopen
from urlparse import urlsplit
import platform
if "Darwin" in platform.system():
        os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

# ------------------------------------------------------------------------------#
# ............................................................................  #
# ................................  scrapergui................................  #
# @author: Jason Giancono............................  #
#..more info at jasongi.com/blackboard-scraper
# todo: ....documentation
# ................better Echo360 scraper
# ................clean up rapyd junk
# ................option to cancel downlaod
# ................option to select individual files
# ................better looking GUI (probably not going to happen)
# ................work for all blackboard not just Curtin
# ................make a setup file
# ------------------------------------------------------------------------------#


valid_chars = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

#sanitizes the filenames for windows (and hopefully other OS' too!)
def sanitize(filename):
    filename = ''.join(c for c in filename if c in valid_chars)
    try:
        while ((filename[len(filename)-1] == ' ') or (filename[len(filename)-1] == '.')):
            filename = filename[:-1]
    except IndexError:
        if len(filename) < 1:
            return 'file_' + filename
        else:
            return filename
    return filename

#class for scraping iLectures from echo360. 
class ILectureUnit():
    def __init__(self, link, name):
        self.link = link
        self.name = name
        self.session = requests.Session()
        
    #scrapes iLectures from a particular rss feed
    #path: path of the root unit directory
    @staticmethod
    def scrape_ilectures(url, path):
        session = requests.Session()
        request = session.get(url)
        soup = BeautifulSoup(request.text, "html.parser")
        alist = []
        blist = []
        dir = 'iLectures'
        unit_name = soup.title.string
        for link in soup.find_all('pubdate'):
            strin = link.string[:-6]
            alist.append(strin)
        for link in soup.find_all('enclosure'):
            blist.append(link.get('url'))
        ii = 0
        for jj in alist:
            ILectureUnit.fetch_video(blist[ii], dir, unit_name, jj, path)
            ii = ii + 1
            
    #downloads a single iLecture video
    #file_url: the url of the video
    #directory: the directory to save to
    #unit_name: the name of the unit
    #file_name: the name of the video
    #path: root directory to save in
    @staticmethod
    def fetch_video(file_url, directory, unit_name, file_name, path):
        session = requests.Session()
        file_name = string.replace(file_name, ':', '-')
        if '.' in file_name:
            format = '.' + file_name.split('.')[1]
        else:
            format = ' '
        while len(format) > 7:
            format = '.' + file_name.split('.')[1]
        while len(directory) > 50:
            directory = directory[:-1]
        directory = string.replace(directory, ':', '-')
        unit_name = string.replace(unit_name, ':', '-')
        thepath = path + '/' + unit_name + '/' + directory + '/'
        while len(thepath + file_name) > 256:
            file_name = file_name[:-9] + format
        if not os.path.isdir(thepath):
            os.makedirs(thepath)
        if not os.path.exists(path + file_name):
            print file_url
            i = session.get(file_url)
            if i.status_code == requests.codes.ok:
                with iopen(thepath + file_name + '.m4v', 'wb') as file:
                    file.write(i.content)
            else:
                return False

#class for scraping blackboard units, simply initialise and call startScrape
class BlackboardUnit():
    def __init__(self, uid, name, session):
        self.uid = uid
        self.name = name
        self.session = session
    
    #downloads a single document - does some checks on the filename to make sure it is legit
    #file url: the url of the file
    #folder name: the subfolder which the file will be downloaded to
    #path: the root path where the unit folder will be
    def fetch_document(self, file_url, folder_name, path):
        while len(folder_name) > 50:
            folder_name = folder_name[:-1]
        while len(self.name) > 50:
            self.name = self.name[:-1]
        folder_name = string.replace(folder_name, ':', ' ')
        self.name = string.replace(self.name, ':', ' ')
        folder_name = sanitize(folder_name)
        self.name = sanitize(self.name)
        urlResponse = self.session.get(file_url, allow_redirects=False)
        if urlResponse.status_code == 302:
            urlpath = urlResponse.headers['location']
        else: 
            urlpath = urlResponse.url
            
        if len(folder_name) > 0:
            thepath = path + '/' + self.name + '/' + folder_name + '/'
        else:
            thepath = path + '/' + self.name + '/'

        name = urlsplit(urlpath)[2].split('/')
        name = name[len(name)-1]
        name = urllib2.unquote(name).decode('utf8')
        while ((len(thepath + name) > 240) or (len(name) > 50)):
            if "." in name:
                filename = name.split('.')
                ext = filename[len(filename)-1]
                prefix = ''
                for x in filename[:-1]:
                    prefix = prefix + x
                name = prefix[:-1] + '.' + ext
            else:
                name = name[:-1]
        name = sanitize(name)
        if name != 'defaultTab' and '.html' not in name:
            if not os.path.isdir(thepath):
                os.makedirs(thepath)

            if (not os.path.exists(thepath + name)):
                print urlpath
                urlResponse = self.session.get(urlpath)
                if urlResponse.status_code == requests.codes.ok:
                    with iopen(thepath + name, 'wb') as file:
                        file.write(urlResponse.content)
                else:
                    return False
     
    #scrapes a page (and all pages on the page)
    #content_id: the content ID number for the page
    #folder_name: the 'name' of the page - this is what the folder will be called when saving documents from this page
    #visitlist: list of previously visited links - to avoid going around in circles
    #path: root path to save all files from the unit
    def recursiveScrape(self, content_id, folder_name, visitlist, path):
        url = \
            'https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_' \
            + self.uid + '_1&content_id=_' + content_id + '_1&mode=reset'
        request = self.session.get(url)
        soup = BeautifulSoup(request.text, "html.parser")
        for htmlLink in soup.find_all('a'):
            link = htmlLink.get('href')
            if '.pdf' in link  or '.doc' in link or 'ppt' in link or 'xid' in link:
                link = string.replace(link, 'https://lms.curtin.edu.au/', '')
                link = string.replace(link, 'lms.curtin.edu.au/', '')
                name = htmlLink.text
                if '1 slide per page' in name or '4 slides per page' in name:
                    name = urlsplit(link)[2].split('/')[-1] + '.pdf'
                try:
                    self.fetch_document('https://lms.curtin.edu.au/' + link, folder_name, path)
                except:
                    print "Error: %s -  %s" % (sys.exc_info()[0], str(sys.exc_info()[1]))
                    
        for htmlLink in soup.find_all('a'):
            link = htmlLink.get('href')
            if link.startswith('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?') or link.startswith('/webapps/blackboard/content/listContent.jsp?'):
                link = link.replace('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_'
                               + self.uid + '_1&content_id=_', '')
                link = link.replace('/webapps/blackboard/content/listContent.jsp?course_id=_'
                               + self.uid + '_1&content_id=_', '')
                link = link.replace('_1&mode=reset', '')
                link = link.replace('_1', '')
                try:
                    if link not in visitlist:
                        visitlist.append(link)
                        visitlist = self.recursiveScrape(link, htmlLink.span.string, visitlist, path)
                except:
                    print "Error: %s -  %s" % (sys.exc_info()[0], str(sys.exc_info()[1]))
        return visitlist

    #starts scraping the unit, path is where it will save the files to
    def startScrape(self, path):
        visitlist = []
        request = self.session.get('https://lms.curtin.edu.au/webapps/blackboard/execute/launcher?type=Course&id=_' + self.uid + '_1')
        soup = BeautifulSoup(request.text, "html.parser")
        for htmlLink in soup.find_all('a'):
            link = htmlLink.get('href')
            if '.pdf' in link or 'xid' in link:
                link.replace('https://lms.curtin.edu.au', '')
                link.replace('lms.curtin.edu.au', '')
                name = htmlLink.text.replace(' ', '')
                if '1slideperpage' in name or '4slideperpage' in name:
                    name = urlsplit(w)[2].split('/')[-1] + '.pdf'  # tempfix for a particular computing unit
                try:
                    self.fetch_document('https://lms.curtin.edu.au/' + link, '', path)
                except:
                    print "Error: %s -  %s" % (sys.exc_info()[0], str(sys.exc_info()[1]))
            elif link.startswith('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?') or link.startswith('/webapps/blackboard/content/listContent.jsp?'):
                link = link.replace('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_'
                               + self.uid + '_1&content_id=_', '')
                link = link.replace('/webapps/blackboard/content/listContent.jsp?course_id=_'
                               + self.uid + '_1&content_id=_', '')
                link = link.replace('_1&mode=reset', '')
                try:
                    if link not in visitlist:
                        visitlist.append(link)
                        visitlist = self.recursiveScrape(link, htmlLink.span.string, visitlist, path)
                except:
                    print "Error: %s -  %s" % (sys.exc_info()[0], str(sys.exc_info()[1]))
        print self.name + ' has finished'

#class for managing a blackboard session. Also holds lists of iLectures and units available to your session.
class BlackboardSession():
    def __init__(self, user, password):
        self.session = requests.Session()
        self.unitList = []
        self.iLectureList = []
        self.password = base64.b64encode(password)
        self.username = user
        self.payload = {
            'login': 'Login',
            'action': 'login',
            'user_id': self.username,
            'encoded_pw': self.password,
            }
        self.url = 'https://lms.curtin.edu.au/webapps/login/'
        self.session.post(self.url, data=self.payload)
        self.getUnitList()
        self.getILectureList()
        
    #gets all available units for current logged in user
    def getUnitList(self):
        response = self.session.get('https://lms.curtin.edu.au/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_3_1')
        soup = BeautifulSoup(response.text, "html.parser")
        for htmlLink in soup.find_all('a'):
            link = htmlLink.get('href')
            if link.startswith(' /webapps/blackboard/execute/launcher?type=Course'
                            ):
                link = \
                    link.replace(' /webapps/blackboard/execute/launcher?type=Course&id=_'
                              , '')
                link = link.replace('_1&url=', '')
                self.unitList.append(BlackboardUnit(link, htmlLink.string.replace('/',''), self.session))
    
    #gets all available iLectures for current logged in user
    def getILectureList(self):
        try:
            for unit in self.unitList:
                request = \
                    self.session.get('https://lms.curtin.edu.au/webapps/blackboard/execute/launcher?type=Course&id=_'
                           + unit.uid + '_1')
                soup = BeautifulSoup(request.text, "html.parser")
                for link in soup.find_all('a'):
                    if 'Echo' in link.get('href'):
                        self.iLectureList.append(ILectureUnit(link.get('href'),
                                        soup.find(id='courseMenu_link'
                                        ).get('title')[9:].replace('/','')))
        except:
            print "Error: %s -  %s" % (sys.exc_info()[0], str(sys.exc_info()[1]))


#start the GUI
def load(RootObj):
    x = 10
    y = 10
    Root = Tk()
    App = loading(Root)
    App.pack(expand='yes', fill='both')
    Root.geometry('200x100+' + str(x + 300) + '+' + str(y + 150))
    Root.title('Loading')
    Root.after(100, functools.partial(update, Root, App))
    Root.mainloop()

def update(Root, App):
    App.progress()
    Root.after(100, functools.partial(update, Root, App))

#GUI stuff
class scrapergui(Frame):

    def __init__(self, Master=None, **kw):
        kw['height'] = 110
        kw['width'] = 110
        self.blackboard_session = None
        self.path = '.'
        apply(Frame.__init__, (self, Master), kw)
        self.__RootObj = Frame
        self.__Frame2 = Frame(self)
        self.__Frame2.pack(side='top', padx=5, pady=0)
        self.__Label3 = Label(self.__Frame2, text='Directory')
        self.__Label3.pack(side='left', padx=5, pady=0)

        self.__Entry3 = Entry(self.__Frame2, width=50)
        self.__Entry3.pack(side='left', padx=5, pady=0)
        self.__Button3 = Button(self.__Frame2, text='browse', width=10)
        self.__Button3.pack(side='left', padx=5, pady=0)
        self.__Button3.bind('<ButtonRelease-1>',
                            self.__on_Button3_ButRel_1)
        self.__Frame5 = Frame(self)
        self.__Frame5.pack(side='top', padx=5, pady=5)
        self.__Frame3 = Frame(self)
        self.__Frame3.pack(side='top', padx=5, pady=0)
        self.__Frame1 = Frame(self)
        self.__Frame1.pack(side='top', padx=5, pady=5)


        self.__LFrame = Frame(self, padx=5, pady=0)
        self.__LFrame.pack(side='left', padx=5, pady=0)
        self.__RFrame = Frame(self, padx=5, pady=0)
        self.__RFrame.pack(side='left', padx=5, pady=0)
        self.__Frame4 = Frame(self.__LFrame, padx=5, pady=5)
        self.__Frame4.pack(side='top', padx=5, pady=5)
        self.__Label9 = Label(self.__Frame4, text='Blackboard Materials'
                              )
        self.__Label9.pack(side='top', padx=5, pady=0)
        self.__Listbox1 = Listbox(self.__Frame4, width=40,
                                  selectmode=EXTENDED)
        self.__Listbox1.pack(side='top', padx=5, pady=5)
        self.__Button1 = Button(self.__Frame4, text='Scrape', width=20)
        self.__Button1.pack(side='bottom')
        self.__Label1 = Label(self.__Frame5, text='login')
        self.__Label1.pack(side='top', padx=5, pady=0)
        self.__Entry1 = Entry(self.__Frame5)
        self.__Entry1.pack(side='top', padx=5, pady=0)
        self.__Label2 = Label(self.__Frame3, text='pass')
        self.__Label2.pack(side='top', padx=5, pady=0)
        self.__Entry2 = Entry(self.__Frame3, show='*')
        self.__Entry2.pack(side='top', padx=5, pady=0)
        self.__Entry2.bind('<KeyRelease-Return>',
                           self.__on_Button2_ButRel_1)
        self.__Button2 = Button(self.__Frame1, text='Login', width=20)
        self.__Button2.pack(side='top', padx=5, pady=5)
        self.__Button2.bind('<ButtonRelease-1>',
                            self.__on_Button2_ButRel_1)
        self.__Button1.bind('<ButtonRelease-1>',
                            self.__on_Button1_ButRel_1)
        self.__Entry3.insert(0, '.')
        self.__Frame7 = Frame(self.__RFrame)
        self.__Frame7.pack(side='top', padx=5, pady=5)
        self.__Label8 = Label(self.__Frame7, text='iLectures')
        self.__Label8.pack(side='top', padx=5, pady=0)
        self.__Listbox2 = Listbox(self.__Frame7, width=40)
        self.__Listbox2.pack(side='top', padx=5, pady=5)
        self.__Button5 = Button(self.__Frame7, text='goto url',
                                width=20)
        self.__Button5.pack(side='top', padx=5, pady=5)
        self.__Button5.bind('<ButtonRelease-1>',
                            self.__on_Button5_ButRel_1)
        self.__Frame6 = Frame(self.__RFrame)
        self.__Frame6.pack(side='top', padx=5, pady=5)
        self.__Frame10 = Frame(self.__Frame6)
        self.__Frame10.pack(side='top', padx=5, pady=0)
        self.__Frame11 = Frame(self.__Frame6)
        self.__Frame11.pack(side='top', padx=5, pady=0)
        self.__Label4 = Label(self.__Frame10, text='Paste iLecture Video RSS URL Here')
        self.__Label4.pack(side='left', padx=5, pady=0)
        self.__Entry4 = Entry(self.__Frame11)
        self.__Entry4.pack(side='left', padx=5, pady=0)
        self.__Button4 = Button(self.__Frame11, text='scrape', width=10)
        self.__Button4.pack(side='left', padx=5, pady=0)
        self.__Button4.bind('<ButtonRelease-1>',
                            self.__on_Button4_ButRel_1)
        self.__Frame9 = Frame(self.__LFrame)
        self.__Frame9.pack(side='top', padx=5, pady=45)
        self.__Frame8 = Frame(self.__RFrame)
        self.__Frame8.pack(side='top', padx=5, pady=15)
        

    #open lms to get the rss link
    def __on_Button5_ButRel_1(self, Event=None):
        for lecs in map(int, self.__Listbox2.curselection()):
            url = self.blackboard_session.iLectureList[lecs].link
            webbrowser.open('https://lms.curtin.edu.au' + url, new=1,
                            autoraise=True)
    
    #scrape ilectures
    def __on_Button4_ButRel_1(self, Event=None):
        self.path = self.__Entry3.get()
        thread.start_new_thread(ILectureUnit.scrape_ilectures, (self.__Entry4.get(), self.path))
        
    #login and get unit list
    def __on_Button2_ButRel_1(self, Event=None):
        self.blackboard_session = BlackboardSession(self.__Entry1.get(), self.__Entry2.get())
        self.__Listbox1.delete(0, END)
        self.__Listbox2.delete(0, END)
        for ii in self.blackboard_session.unitList:
            self.__Listbox1.insert(END, ii.name)
        for ii in self.blackboard_session.iLectureList:
            self.__Listbox2.insert(END, ii.name)
        
    #GUI browse button
    def __on_Button3_ButRel_1(self, Event=None):
        filename = askdirectory()
        self.__Entry3.delete(0, END)
        self.__Entry3.insert(0, filename)
        
    #scrape units selected
    def __on_Button1_ButRel_1(self, Event=None):
        self.path = self.__Entry3.get()
        for unit in map(int, self.__Listbox1.curselection()):
            bbunit = self.blackboard_session.unitList[unit]
            thread.start_new_thread(bbunit.startScrape, (self.path,))



# Adjust sys.path so we can find other modules of this project
import sys
if '.' not in sys.path:
    sys.path.append('.')

# Put lines to import other modules of this project here
#init the program
if __name__ == '__main__':
    Root = Tk()
    App = scrapergui(Root)
    App.pack(expand='yes', fill='both')
    Root.geometry('600x600+10+10')
    Root.title('Blackboard/iLecture Scraper - By Jason Giancono')
    Root.mainloop()


            
