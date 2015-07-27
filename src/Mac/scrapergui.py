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
# ................better descriptions for iLecture links - done
# ................better looking GUI (probably not going to happen)
# ................work for all blackboard not just Curtin
# ................use newer thread library, make it OO
# ................make a setup file
# ------------------------------------------------------------------------------#

unitlist = []
ileclist = []

s = 0
path = '.'

valid_chars = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
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
#terrible name for function. This fetches media (be it pdf, ppt, doc, etc)
#file_url: url of the media
#s: session object from Requests
#o: subpage/folder name
#k: unit name
#p: system path (specified in GUI)
def requests_image(
	file_url,
	s,
	o,
	k,
	path,
	):

	while len(o) > 50:
		o = o[:-1]
	while len(k) > 50:
		k = k[:-1]
	o = string.replace(o, ':', ' ')
	k = string.replace(k, ':', ' ')
	o = sanitize(o)
	k = sanitize(k)
	thepath = path + '/' + k + '/' + o + '/'
	if not os.path.isdir(thepath):
		os.makedirs(thepath)
	i = s.get(file_url, allow_redirects=False)
	if i.status_code == 302:
		urlpath = i.headers['location']
	else: 
		urlpath = i.url
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
	if not os.path.exists(thepath + name):
		print urlpath
		i = s.get(urlpath)
		if i.status_code == requests.codes.ok:
			with iopen(thepath + name, 'wb') as file:
				file.write(i.content)
		else:
			return False

#this fetches the video for parsing the echo rss feed
#file_url: url of the media
#s: session object from Requests
#o: subpage/folder name (this should be empty, not sure why it exists)
#k: unit name
#file_name name of video/lecture
#path: system path (specified in GUI)
def requests_video(
	file_url,
	s,
	o,
	k,
	file_name,
	path,
	):
	file_name = string.replace(file_name, ':', '-')
	if '.' in file_name:
		format = '.' + file_name.split('.')[1]
	else:
		format = ' '
	while len(format) > 7:
		format = '.' + file_name.split('.')[1]
	while len(o) > 50:
		o = o[:-1]
	o = string.replace(o, ':', '-')
	k = string.replace(k, ':', '-')
	thepath = path + '/' + k + '/' + o + '/'
	while len(thepath + file_name) > 256:
		file_name = file_name[:-9] + format
	if not os.path.isdir(thepath):
		os.makedirs(thepath)
	if not os.path.exists(path + file_name):
		print file_url
		i = s.get(file_url)
		if i.status_code == requests.codes.ok:
			with iopen(thepath + file_name + '.m4v', 'wb') as file:
				file.write(i.content)
		else:
			return False
			
#This grabs all the ilecture videos in an rss
#url: url of the rss feed
#s: session object
#path: path (specified in GUI)
def ilec(url, s, path):
	r = s.get(url)
	data = r.text
	soup = BeautifulSoup(data)
	alist = []
	blist = []
	dir = 'iLectures'
	title = soup.title.string
	for link in soup.find_all('pubdate'):
		strin = link.string[:-6]
		alist.append(strin)
	for link in soup.find_all('enclosure'):
		blist.append(link.get('url'))
	ii = 0
	for jj in alist:
		requests_video(
			blist[ii],
			s,
			dir,
			title,
			jj,
			path,
			)
		ii = ii + 1

#scrapes a blackboard page (and every page it links to)
#m: unit id
#t: content id
#s: session object
#o: file name
#k: subpage/folder name
#visitlist: list of pages visted (used to stop infinite loops)
#path: path specified in GUI
def scraperec(
	m,
	t,
	s,
	o,
	k,
	visitlist,
	path,
	):

	url = \
		'https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_' \
		+ m + '_1&content_id=_' + t + '_1&mode=reset'
	r = s.get(url)

	data = r.text
	soup = BeautifulSoup(data)
	for pdf in soup.find_all('a'):
		w = pdf.get('href')
		if '.pdf' in w  or '.doc' in w or 'ppt' in w or 'xid' in w:
			w = string.replace(w, 'https://lms.curtin.edu.au/', '')
			w = string.replace(w, 'lms.curtin.edu.au/', '')
			name = pdf.text
			if '1 slide per page' in name or '4 slides per page' in name:
				name = urlsplit(w)[2].split('/')[-1] + '.pdf'  # fuck dave
			try:
				requests_image(
					'https://lms.curtin.edu.au/' + w,
					s,
					o,
					k,
					path,
					)
			except:
				pass
	for link in soup.find_all('a'):
		l = link.get('href')
		if l.startswith('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?'
						) \
			or l.startswith('/webapps/blackboard/content/listContent.jsp?'
							):
			l = \
				l.replace('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_'
						   + m + '_1&content_id=_', '')
			l = \
				l.replace('/webapps/blackboard/content/listContent.jsp?course_id=_'
						   + m + '_1&content_id=_', '')
			l = l.replace('_1&mode=reset', '')
			l = l.replace('_1', '')
			C = l
			try:
				if C not in visitlist:
					visitlist.append(C)
					visitlist = scraperec(
						m,
						l,
						s,
						link.span.string,
						k,
						visitlist,
						path,
						)
			except:
				pass
	return visitlist

#scrapes every page the main unit page links to
#m: unit id
#s: session object
#o: subpage/folder name
#path: path specified in GUI

def scrape(
	m,
	s,
	o,
	path,
	):

	visitlist = []
	r = \
		s.get('https://lms.curtin.edu.au/webapps/blackboard/execute/launcher?type=Course&id=_'
			   + m + '_1')
	data = r.text
	soup = BeautifulSoup(data)
	for pdf in soup.find_all('a'):
		w = pdf.get('href')
		if '.pdf' in w or 'xid' in w:
			w.replace('https://lms.curtin.edu.au', '')
			w.replace('lms.curtin.edu.au', '')
			name = pdf.text.replace(' ', '')
			if '1slideperpage' in name or '4slideperpage' in name:
				name = urlsplit(w)[2].split('/')[-1] + '.pdf'  # fuck dave
			try:
				requests_image(
				'https://lms.curtin.edu.au/' + w,
				s,
				'',
				o,
				path,
				)
			except:
				pass
	for link in soup.find_all('a'):
		l = link.get('href')
		if l.startswith('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?'
						) or l.startswith('/webapps/blackboard/content/listContent.jsp?'
						):
			l = \
				l.replace('https://lms.curtin.edu.au/webapps/blackboard/content/listContent.jsp?course_id=_'
						   + m + '_1&content_id=_', '')
			l = \
				l.replace('/webapps/blackboard/content/listContent.jsp?course_id=_'
						   + m + '_1&content_id=_', '')
			l = l.replace('_1&mode=reset', '')
			C = l
			try:
				if C not in visitlist:
					visitlist.append(C)
					visitlist = scraperec(
						m,
						l,
						s,
						link.span.string,
						o,
						visitlist,
						path,
						)
			except:
				pass
	print o + ' has finished'

#starts the login session
def login(user, password):
	unitlist = []
	ileclist = []
	password = base64.b64encode(password)
	payload = {
		'login': 'Login',
		'action': 'login',
		'user_id': user,
		'encoded_pw': password,
		}
	url = 'https://lms.curtin.edu.au/webapps/login/'

	with requests.Session() as s:
		s.post(url, data=payload)
		r = \
			s.get('https://lms.curtin.edu.au/webapps/portal/execute/tabs/tabAction?tab_tab_group_id=_3_1'
				  )
		data = r.text
		soup = BeautifulSoup(data)

	for link in soup.find_all('a'):
		l = link.get('href')
		if l.startswith(' /webapps/blackboard/execute/launcher?type=Course'
						):
			l = \
				l.replace(' /webapps/blackboard/execute/launcher?type=Course&id=_'
						  , '')
			l = l.replace('_1&url=', '')
			unitlist.append([l, link.string.replace('/','')])
	for unit in unitlist:
		r = \
			s.get('https://lms.curtin.edu.au/webapps/blackboard/execute/launcher?type=Course&id=_'
				   + unit[0] + '_1')
		data = r.text
		soup = BeautifulSoup(data)
		for link in soup.find_all('a'):
			if 'Echo' in link.get('href'):
				ileclist.append([link.get('href'),
								soup.find(id='courseMenu_link'
								).get('title')[9:].replace('/','')])
	return [s, unitlist, ileclist]

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

#I actually have no idea
def update(Root, App):
	App.progress()
	Root.after(100, functools.partial(update, Root, App))

#loading bar pop up
class loading(Frame):

	def __init__(self, Master=None, **kw):
		self.__loadpoint = 0
		apply(Frame.__init__, (self, Master), kw)
		self.__Frame2 = Frame(self)
		self.__Frame2.pack(side='top', padx=5, pady=0)
		self.__Label3 = Label(self.__Frame2, text='Loading...')
		self.__Label3.pack(side='top', padx=5, pady=5)

		self.__Frame3 = Frame(self)
		self.__Frame3.pack(side='top', padx=5, pady=0)
		self.__Canvas1 = Canvas(self.__Frame3, width=100, height=50)
		self.__Canvas1.pack(side='top', padx=5, pady=0)
		self.__Canvas1.create_rectangle(0, 0, 100, 50, fill='grey')
		self.__loadbar = self.__Canvas1.create_rectangle(0, 0,
				self.__loadpoint + 10, 50, fill='blue')
		self.__loadpoint += 10

	def progress(self):
		self.__Canvas1.delete(self.__loadbar)
		self.__loadbar = \
			self.__Canvas1.create_rectangle(self.__loadpoint, 0,
				self.__loadpoint + 10, 50, fill='blue')
		self.__loadpoint += 10
		if self.__loadpoint > 90:
			self.__loadpoint = 0

#GUI stuff
class scrapergui(Frame):

	def __init__(self, Master=None, **kw):
		kw['height'] = 110
		kw['width'] = 110

		#
		# Your code here........

		#

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
		if (datetime.datetime.now() < datetime.datetime(2015,3,31)):
			self.__FrameLink = Frame(self)
			self.__FrameLink.pack( padx=5, pady=0)
			self.__FrameLink2 = Frame(self)
			self.__FrameLink2.pack(side='bottom', padx=5, pady=5)
			self.__lbl_link = Label(self, text="I'm running for University Council, find out more here:  jasongi.com/university-council-elections", fg="Blue", cursor="hand2")
			self.__lbl_link.pack(side='bottom')
			self.__lbl_link.bind("<Button-1>", self.__link_callback)


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
		

		#
		# Your code here
		#
	#
	# Start of event handler methods
	#
	def __link_callback(self, Event=None):
		webbrowser.open_new(r"jasongi.com/university-council-elections")
	def __on_Button5_ButRel_1(self, Event=None):
		global ileclist
		for lecs in map(int, self.__Listbox2.curselection()):
			url = ileclist[lecs][0]
			webbrowser.open('https://lms.curtin.edu.au' + url, new=1,
							autoraise=True)
	
	def __on_Button4_ButRel_1(self, Event=None):
		global s
		global path
		path = self.__Entry3.get()
		thread.start_new_thread(ilec, (self.__Entry4.get(), s, path))
	#login and get unit list
	def __on_Button2_ButRel_1(self, Event=None):
		global s
		global unitlist
		global ileclist
		#proc = multiprocessing.Process(target=load,
		#		args=(self.__RootObj, ))
		#proc.start()
		z = login(self.__Entry1.get(), self.__Entry2.get())
		s = z[0]
		unitlist = z[1]
		ileclist = z[2]
		self.__Listbox1.delete(0, END)
		self.__Listbox2.delete(0, END)
		for ii in unitlist:
			self.__Listbox1.insert(END, ii[1])
		for ii in ileclist:
			self.__Listbox2.insert(END, ii[1])
		#proc.terminate()
		
	#GUI browse button
	def __on_Button3_ButRel_1(self, Event=None):
		filename = askdirectory()
		self.__Entry3.delete(0, END)
		self.__Entry3.insert(0, filename)
	#scrape everything selected
	def __on_Button1_ButRel_1(self, Event=None):
		global s
		global path
		path = self.__Entry3.get()
		slist = ''
		for unit in map(int, self.__Listbox1.curselection()):
			uid = unitlist[unit][0]
			uname = unitlist[unit][1]
			thread.start_new_thread(scrape, (uid, s, uname, path))


	#
	# Start of non-Rapyd user code
	#

	# --------------------------------------------------------------------------#
	# User code should go after this comment so it is inside the "try".........#
	# .... This allows rpErrorHandler to gain control on an error so it........ #
	# .... can properly display a Rapyd-aware error message.....................#
	# --------------------------------------------------------------------------#

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
	Root.geometry('650x600+10+10')
	Root.title('Blackboard/iLecture Scraper - By Jason Giancono')
	Root.mainloop()

	# --------------------------------------------------------------------------#
	# User code should go above this comment.................................  #
	# --------------------------------------------------------------------------#


			
