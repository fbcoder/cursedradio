##########################################################################
# Copyright 2012 fbcoder
#
# This file is part of CursedRadio
#
# Radio Tray is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 1 of the License, or
# (at your option) any later version.
#
# Radio Tray is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Radio Tray.  If not, see <http://www.gnu.org/licenses/>.
#
##########################################################################
import sys
import curses
import threading
import time
import logging
from random import randint

class Animation:
    def __init__(self,size):
        self.frameCount = 0
        self.numFrames = 0
        self.frames = []
        self.size = size
        self.cycles = 0
        self.maxCycles = 0
        self.maxCyclesCallback = 0
        
    def init(self,maxCycles,maxCyclesCallback):
        self.reset()
        self.maxCycles = maxCycles
        self.maxCyclesCallback = maxCyclesCallback
                    
    def addFrame(self,frameLines):
        if len(frameLines) != self.size['height']:
            raise Exception("Invalid number of lines in animation frame %d" % self.numFrames)
        for f in frameLines:
            if len(f) != self.size['width']:
                raise Exception("Invalid number of characters in frameline %d" % frameLines.index(f))
        self.frames.append(frameLines)
        self.numFrames += 1
        
    def getNextFrame(self):                        
        self.frameCount += 1
        if self.frameCount >= self.numFrames:
            self.frameCount = 0
            self.cycles += 1
            if self.cycles >= self.maxCycles:
                self.maxCyclesCallback()
                return None
        return self.frames[self.frameCount]    
                
    def reset(self):
        self.frameCount = 0
        self.cycles = 0

              
class CursesWindow:
    def __init__(self,drawCallback,windowProperties,winobj=None):
        self.drawCallback = drawCallback
        self.logger = logging.getLogger('curses')
        self.window = None        
        self.windowSize = None
        if winobj != None:
            self.setWindow(winobj)        
        self.border = False
        self.borderColor = 0
        if 'border' in windowProperties.keys():
            self.border = windowProperties['border']
            if 'borderColor' in windowProperties.keys():
                self.borderColor = windowProperties['borderColor']
        self.minWidth = 1
        self.minHeight = 1
        #self.minWidth = windowProperties['minWidth']
        #self.minHeight = windowProperties['minHeight']
        #self.fixed = windowProperties['fixed']
        self.active = True
    
    def setWindow(self,winobj):
        self.window = winobj
        self.windowSize = {'width':self.window.getmaxyx()[1],'height':self.window.getmaxyx()[0]}
    
    def reportWindowSize(self):
        self.logger.debug("Geometry of this window (w x h): %d x %d" % (self.windowSize['width'],self.windowSize['height']))
        
    def resize(self,newSize):
        if 'width' in newSize.keys() and 'height' in newSize.keys():
            self.logger.debug("** Attempt window resize **")
            self.logger.debug("Window should be resized to %d x %d."%(newSize['width'],newSize['height']))
            self.window.resize(newSize['height'],newSize['width'])            
            self.windowSize = {'width':self.window.getmaxyx()[1],'height':self.window.getmaxyx()[0]}
            self.reportWindowSize()
            if self.windowSize['height'] < self.minHeight or self.windowSize['width'] < self.minWidth:
                self.active = False
            else:
                self.active = True
        else:
            raise Exception("newSize must contain height and width.")
        
    def reposition(self,top,left):
        try:
            self.window.mvwin(top,left)
        except:
            self.active=False
            self.logger.debug("Could not move window to %d,%d." % (top,left))
            self.reportWindowSize()
        else:
            self.active=True
    
    def startDrawing(self):
        self.window.erase()
        if self.active:
            if self.border:
                if self.borderColor > 0:
                    pass
                else:
                    self.window.box()
                
    def endDrawing(self):        
        self.window.refresh()
    
    def draw(self):
        self.startDrawing()
        if self.active:
            self.drawCallback()
        self.endDrawing()
        
    def getMaxLength(self,offset=0):
        #window width - borders - offset
        borderChars = 0
        if self.border:
            borderChars = 2
        return self.windowSize['width'] - borderChars - offset
        
    def fitString(self,s,offset=0):
        return s[:self.getMaxLength(offset)]
        
    def getWidth(self):
        return self.windowSize['width']
        
    def getHeight(self):
        return self.windowSize['height']    
        
    def eraseLine(self,y,reverse=False):
        reverseFlag = 0
        x = 0
        width = self.windowSize['width'] - 1
        if self.border:
            x = 1
            width -= 2
        paddingString = "".ljust(width)    
        if reverse:    
            reverseFlag = curses.A_REVERSE        
        self.printStringQuick(y,x,paddingString,reverseFlag)    
        
    def getTotalLength(self,strings):
        l = 0
        for s in strings:
            if 'text' in s.keys():
                l += len(s['text'])
        if l >= self.windowSize['width']:
            l = self.windowSize['width']
        return l        
    
    def printSubString(self,y,x,s,attrs):
        colorFlag = 0
        reverseFlag = 0
        boldFlag = 0
        if 'color' in attrs.keys():
            colorFlag = curses.color_pair(attrs['color'])
        if 'reverse' in attrs.keys():
            reverseFlag = curses.A_REVERSE
        if 'bold' in attrs.keys():
            boldFlag = curses.A_BOLD        
        self.printStringQuick(y,x,s,(colorFlag | reverseFlag | boldFlag))        
        
    def printString(self,props):
        w = self.windowSize['width']
        x = props['x']
        y = props['y']
        if 'centered' in props.keys(): 
            x = (w - self.getTotalLength(props['strings'])) / 2
        for thisString in props['strings']:
            if x < w:
                if 'text' in thisString.keys():
                    s = thisString['text']
                    l = len(s)
                    if (x + l) >= w:
                        s = self.fitString(s,x)
                    self.printSubString(y,x,s,thisString)    
                    x += l
            else:
                break
            
    def printStringQuick(self,y,x,s,attribs):
        try:
            self.window.addstr(y,x,s,attribs)
        except:    
            self.logger.debug("** FAILED PRINT **")
            self.logger.debug("Could not print string '%s', of length %d on coords(y,x) (%d,%d)." % (s,len(s),y,x,))
            self.logger.debug("Length of string + x = %d." % (x + len(s)))
            self.reportWindowSize()        


class BookmarkSelector(CursesWindow):
    def __init__(self,provider,urlChangeCallback):
        # Create window with border
        CursesWindow.__init__(self,self.drawImpl,{'border':True})
        # Process arguments
        self.provider = provider
        self.urlChangeCallback = urlChangeCallback
        
        # Handle bookmarkvars
        self.radioStations = []   
        self.selectedGroup = 0
        self.selectedStation = 0
        self.depth = 0       
        self.menuLines = 3
        self.scrolled = 0
        self.menuCursor = 0
        self.currentMenu = []
        
        self.getRadios()
        self.populateMenu()
        
    def getRadios(self):
        radioGroups = self.provider.listGroupNames()
        for groupName in radioGroups:
            if groupName != "root":
                stationsInGroup = [] 
                stationNames = self.provider.listRadiosInGroup(groupName)
                for sName in stationNames:
                    url = self.provider.getRadioUrl(sName)
                    stationsInGroup.append({'name':sName,'url':url})
                self.radioStations.append({'name':groupName,'stationList':stationsInGroup})
                
    def populateMenu(self):
        self.currentMenu = []
        if self.depth == 0:
            for group in self.radioStations:
                self.currentMenu.append(group['name'])
        elif self.depth == 1:
            for station in self.radioStations[self.selectedGroup]['stationList']:
                self.currentMenu.append(station['name'])
                            
    def drawImpl(self):
        self.menuLines = CursesWindow.getHeight(self) - 2  
        selectedItem = self.menuCursor + self.scrolled      
        for i in range(0,self.menuLines):
            itemIndex = i + self.scrolled
            if itemIndex < len(self.currentMenu):
                selector = "   "
                if itemIndex == selectedItem:
                    selector = ">> "
                CursesWindow.printString(self,{'y':i+1,'x':1,'strings':[{'text':selector,'color':4},{'text':self.currentMenu[itemIndex],'color':2}]})
        
    def goBack(self):
        if self.depth == 1:
            self.depth = 0
            self.menuIndex = 0
            self.populateMenu()
            
    def getIndex(self):
        return self.scrolled + self.menuCursor
        
    def resetCursor(self):
        self.scrolled = 0
        self.menuCursor = 0
        
    def select(self):
        if self.depth == 0:
            self.depth = 1
            self.selectedGroup = self.getIndex()
            self.populateMenu()
            self.resetCursor()
        elif self.depth == 1:
            self.selectedStation = self.getIndex()
            self.resetCursor()
            thisStation = self.radioStations[self.selectedGroup]['stationList'][self.selectedStation]
            self.urlChangeCallback(thisStation['url'],True,thisStation['name'])
            
    def getMaxScroll(self):
        return len(self.currentMenu) - self.menuLines
            
    def menuUp(self):
        self.menuCursor -= 1
        if self.menuCursor < 0:
            self.menuCursor = 0
            self.scrolled -= 1
            if self.scrolled < 0:
                self.scrolled = 0
    
    def menuDown(self):
        maxScroll = self.getMaxScroll()
        self.menuCursor += 1
        if self.menuCursor >= self.menuLines:
            self.menuCursor = self.menuLines - 1
            self.scrolled += 1
            if self.scrolled >= maxScroll:
                self.scrolled = maxScroll

                
class TitleBar(CursesWindow):
    def __init__(self,station):
        CursesWindow.__init__(self,self.drawImpl,{'border':False})        
        self.frameCount = 0
        self.currentStation = station
        
    def drawImpl(self):        
        title = ""
        if self.frameCount == 0:
            title = "** CursedRadio -- v0.1 **"
            self.frameCount += 1
        elif self.frameCount == 1:
            title = self.currentStation['url']
            if self.currentStation['bookmarked']:
                self.frameCount += 1
            else:
                self.frameCount = 0
        elif self.frameCount == 2:
            title = self.currentStation['name']
            self.frameCount = 0
        else:
            pass
        CursesWindow.eraseLine(self,0,True)
        CursesWindow.printString(self,{'x':0,'y':0,'strings':[{'text':title,'reverse':True}],'centered':True})        

    def setStation(self,newStation):
        self.currentStation = newStation
        
class MainWindow(CursesWindow):
    def __init__(self,state):
        CursesWindow.__init__(self,self.drawImpl,{'border':True})
        self.playerState = state
        
    def drawImpl(self):
        CursesWindow.printString(self,{'y':1,'x':1,'strings':[{'text':"Artist | ",'color':4},\
                                                              {'text':self.playerState['artist'],'color':4,'bold':True}]})
        CursesWindow.printString(self,{'y':2,'x':1,'strings':[{'text':"Title  | ",'color':5},\
                                                              {'text':self.playerState['title'],'color':5,'bold':True}]})
        CursesWindow.printString(self,{'y':3,'x':1,'strings':[{'text':"State  | ",'color':2},\
                                                              {'text':self.playerState['streamState'],'color':2,'bold':True}]})
                                                              
    def setState(self,newState):
        self.playerState = newState

        
class AnimationWindow(CursesWindow):
    defaultAnimation = Animation({'height':3,'width':7})
    defaultAnimation.addFrame([ "   @   ",\
                                "   |   ",\
                                " __|__ "])
    defaultAnimation.addFrame([ "  (@)  ",\
                                "   |   ",\
                                " __|__ "])
    defaultAnimation.addFrame([ " ((@)) ",\
                                "   |   ",\
                                " __|__ "])                                
    defaultAnimation.addFrame([ "(((@)))",\
                                "   |   ",\
                                " __|__ "])
    defaultAnimation.addFrame([ "(( @ ))",\
                                "   |   ",\
                                " __|__ "])
    defaultAnimation.addFrame([ "(  @  )",\
                                "   |   ",\
                                " __|__ "])
                                
    millAnimation = Animation({'height':3,'width':7})
    millAnimation.addFrame([ "   !   ",\
                             "   |   ",\
                             " __|__ "])
    millAnimation.addFrame([ "   ./  ",\
                             "  /|   ",\
                             " __|__ "])                             
    millAnimation.addFrame([ " __.__ ",\
                             "   |   ",\
                             " __|__ "])
    millAnimation.addFrame([ "  \.   ",\
                             "   |\  ",\
                             " __|__ "])
                             
    heliAnimation = Animation({'height':3,'width':7})
    heliAnimation.addFrame([ ">      ",\
                             ">      ",\
                             ">      "])
    heliAnimation.addFrame([ " >     ",\
                             " >     ",\
                             " >     "])
    heliAnimation.addFrame([ "  >    ",\
                             "  >    ",\
                             "  >    "])
    heliAnimation.addFrame([ "   >   ",\
                             "   >   ",\
                             "   >   "])
    heliAnimation.addFrame([ "    >  ",\
                             "    >  ",\
                             "    >  "])
    heliAnimation.addFrame([ "     > ",\
                             "     > ",\
                             "     > "])
    heliAnimation.addFrame([ "      >",\
                             "      >",\
                             "      >"])
    heliAnimation.addFrame([ "       ",\
                             "       ",\
                             "       "])                            
                             

    animationList=[defaultAnimation,millAnimation,heliAnimation]                         
    
    def __init__(self):
        CursesWindow.__init__(self,self.drawImpl,{'border':True,'minWidth':9,'minHeight':5,'fixed':True})
        self.animation = False
        self.randomColor = 1
        self.thisAnimation = self.millAnimation
        self.maxRuns = 10
        self.availableColors = [2,4,5]
        
    def pickNewAnimation(self):
        r = randint(0,len(self.animationList)-1)
        self.randomColor = self.availableColors[randint(0,len(self.availableColors) - 1)]
        self.thisAnimation = self.animationList[r]
        self.thisAnimation.init(self.maxRuns,self.runCompleted)
    
    def runCompleted(self):
        self.pickNewAnimation()
    
    def drawImpl(self):        
        if self.animation:
            aniFrame = self.thisAnimation.getNextFrame()
            if aniFrame != None:
                CursesWindow.printString(self,{'y':1,'x':1,'strings':[{'text':aniFrame[0],'color':self.randomColor}]})
                CursesWindow.printString(self,{'y':2,'x':1,'strings':[{'text':aniFrame[1],'color':self.randomColor}]})
                CursesWindow.printString(self,{'y':3,'x':1,'strings':[{'text':aniFrame[2],'color':self.randomColor}]})
            else:
                #maxRuns reached
                CursesWindow.printString(self,{'y':2,'x':1,'strings':[{'text':"next"}],'centered':True})
        
    def setAnimation(self,newAnimationState):
        self.animation = newAnimationState
        if self.animation == False:
            self.thisAnimation.reset()
        else:
            self.pickNewAnimation()

    
class KeyInfoBar(CursesWindow):
    def __init__(self,mode):
        CursesWindow.__init__(self,self.drawImpl,{'border':False})
        self.firstCharColor = 4
        self.mode = mode
    
    def drawImpl(self):
        viewTextFirstChar = {'text':"m",'color':self.firstCharColor}
        viewText = {'text':"ain view | "}
        if self.mode == CursesThread.MODE_MAIN:
            viewTextFirstChar = {'text':"b",'color':self.firstCharColor}
            viewText = {'text':"ookmarks view | "}        
        CursesWindow.printString(self,{'y':0,'x':0,'strings':[{'text':"p",'color':self.firstCharColor}, \
                                                              {'text':"lay/pause | "}, \
                                                              viewTextFirstChar, \
                                                              viewText, \
                                                              {'text':"q",'color':self.firstCharColor}, \
                                                              {'text':"uit"}],'centered':True})        
    
    def setMode(self,newMode):
        self.mode = newMode
        
class BufferWindow(CursesWindow):
    def __init__(self,state):
        CursesWindow.__init__(self,self.drawImpl,{'border':False})
        self.myBuffer = 0
        self.playerState = state
        
    def drawImpl(self):
        self.myBuffer = self.playerState['buffer']
        
        progressBarPart = 100.0 / (self.windowSize['width'] - 2)
        chars = int(self.myBuffer / progressBarPart)
        charsLeft = (self.windowSize['width'] - 2) - chars
        progressBar = "".ljust(chars,"#") + ("".ljust(charsLeft," ")) 
                
        CursesWindow.printString(self,{'y':0,'x':1,'strings':[{'text':progressBar,'color':3}]})            
        
    def setState(self,newState):
        self.playerState = newState

            
class CursesThread(threading.Thread):
    MODE_MAIN = 0
    MODE_BOOKMARKS = 1
        
    def __init__(self,audioplayer,provider,mainloop):
        threading.Thread.__init__(self)        
        self.player = audioplayer
        self.provider = provider
        self.mainloop = mainloop
        self.logger = logging.getLogger('curses')
        self.bookmarkSelector = BookmarkSelector(self.provider,self.urlChange)
        
        self.mode = self.MODE_MAIN        
                
        self.screen = None
        self.screenSize={'width':0,'height':0}
        
        self.mainWindow = None        
        self.labelBar = None
        self.animationWindow = None
        self.bufferWindow = None
           
        self.titleFrameCount = 0
        
        self.playerState={'artist':"",'title':"",'streamState':"",'buffer':0}
        self.currentStation={'url':"http://icecast.omroep.nl/radio1-bb-mp3",'bookmarked':False,'name':"Radio1 NL"}
        
    def run(self):
        #Initialize Curses
        self.screen = curses.initscr()
        self.screen.refresh()
        
        curses.noecho()
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_BLUE, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        
        self.screen.keypad(1)
        self.screen.nodelay(1)        
        self.screenSize={'width':self.screen.getmaxyx()[1],'height':self.screen.getmaxyx()[0]}
        
        self.initWindows()
        self.labelBar.draw()
        c = ""
        ticks = 0
        while c != ord("q"):
            #refresh windows on certain intervals            
            if ticks % 5 == 0:
                if self.mode == self.MODE_MAIN:
                    self.mainWindow.draw()
                else:
                    self.bookmarkSelector.draw()
                self.animationWindow.draw()
                self.bufferWindow.draw()
                            
            if ticks % 30 == 0:
                self.titleBar.draw()
            
            c = self.screen.getch(7,0)
            ticks += 1
            if ticks > 29:
                ticks = 0
            #sleep for one tick
            time.sleep(.1)
                        
            #get keys
            if self.windowSizeChanged():
                self.updateAllWindows()
            self.handleKeyPress(c)
        
        self.endCurses()        
    
    def endCurses(self):      
        self.screen.keypad(0)
        curses.endwin()
        self.mainloop.quit()
     
    #Give all windows new dimensions if necessary or reposition them.
    def updateAllWindows(self):    
        self.screen.erase()
        self.screen.refresh()
        width = self.screenSize['width']
        height = self.screenSize['height'] 
        self.logger.debug("Screen is now (w x h): %d x %d" % (width,height))
        self.titleBar.resize({'width':width,'height':1})
        self.titleBar.draw()
        
        self.mainWindow.resize({'width':width-10,'height':5})                        
        self.bookmarkSelector.resize({'width':width-10,'height':5})                
        if self.mode == self.MODE_BOOKMARKS:
            self.bookmarkSelector.draw()
        else:
            self.mainWindow.draw()   
            
        self.animationWindow.reposition(1,width-10)        
        self.animationWindow.draw()
        
        self.labelBar.resize({'width':width-10,'height':1})
        self.labelBar.draw()
        
        self.bufferWindow.reposition(6,width-10)        
        self.bufferWindow.draw()
    
    def windowSizeChanged(self):
        newSize={'width':self.screen.getmaxyx()[1],'height':self.screen.getmaxyx()[0]}
        if newSize['width'] == self.screenSize['width']:
            if newSize['height'] == self.screenSize['height']:
                return False                
        self.screenSize['width'] = newSize['width']
        self.screenSize['height'] = newSize['height']
        self.logger.debug("** RESIZE EVENT **")
        self.logger.debug("Screen is now (w x h): %d x %d" % (self.screenSize['width'],self.screenSize['height']))
        return True        
        
    def urlChange(self,newUrl,newBookmarked=False,newStationName=None):
        self.currentStation['url'] = newUrl
        self.currentStation['bookmarked'] = newBookmarked
        if self.currentStation['bookmarked']:
            self.currentStation['name'] = newStationName
        else:
            self.currentStation['name'] = None
        self.player.stop()
        self.player.start(self.currentStation['url'])
        self.titleBar.setStation(self.currentStation)
        
    def handleKeyPress(self,c):
        if self.mode == self.MODE_MAIN:
                if c == ord("p"):
                    if self.playerState['streamState'] != "playing":
                        self.player.start(self.currentStation['url'])
                    else:
                        self.player.stop()
                    self.mainWindow.draw()                    
                if c == ord("b"):
                    self.mode = self.MODE_BOOKMARKS
                    self.bookmarkSelector.draw()
                    self.labelBar.setMode(self.mode)
                    self.labelBar.draw()
        elif self.mode == self.MODE_BOOKMARKS:
            if c == ord("m"):
                self.mode = self.MODE_MAIN
                self.mainWindow.draw()
                self.labelBar.setMode(self.mode)
                self.labelBar.draw()
            if c == curses.KEY_UP:
                self.bookmarkSelector.menuUp()
                self.bookmarkSelector.draw()
            if c == curses.KEY_DOWN:
                self.bookmarkSelector.menuDown()
                self.bookmarkSelector.draw()
            if c == ord("e"):
                self.bookmarkSelector.select()
                self.bookmarkSelector.draw()
            if c == curses.KEY_LEFT:
                self.bookmarkSelector.goBack()
                self.bookmarkSelector.draw()
        else:
            pass
    
    def initWindows(self):
        self.titleBar = TitleBar(self.currentStation)
        self.titleBar.setWindow(curses.newwin(1,self.screenSize['width'],0,0))
        self.mainWindow = MainWindow(self.playerState)
        self.mainWindow.setWindow(curses.newwin(5,self.screenSize['width']-10,1,0))        
        self.bookmarkSelector.setWindow(curses.newwin(5,self.screenSize['width']-10,1,0))
        self.animationWindow = AnimationWindow()
        self.animationWindow.setWindow(curses.newwin(5,9,1,self.screenSize['width']-10))
        self.labelBar = KeyInfoBar(self.mode)
        self.labelBar.setWindow(curses.newwin(1,self.screenSize['width']-10,6,0))
        self.bufferWindow = BufferWindow(self.playerState)
        self.bufferWindow.setWindow(curses.newwin(1,9,6,self.screenSize['width']-10))
        
    def setTerminalTitle(self):
        termTitle = "%s - %s (%s)" % (self.playerState['artist'],self.playerState['title'],self.currentStation['name'])
        sys.stdout.write("\x1b]2;%s\x07" % termTitle)
                            
    def updateSong(self, data):
        if('artist' in data.keys()):
            self.playerState['artist'] = data['artist']
        else:
            self.playerState['artist'] = ""
        if('title' in data.keys()):
            self.playerState['title'] = data['title']
            if self.playerState['artist'] == "":
                if ' - ' in self.playerState['title']:
                    [self.playerState['artist'], self.playerState['title']] = self.playerState['title'].split(' - ',1)
            self.mainWindow.setState(self.playerState)
            self.setTerminalTitle()
        
    def updateState(self, data):
        if('state' in data.keys()):
            self.playerState['streamState'] = data['state']
            self.animationWindow.setAnimation(False)
            if self.playerState['streamState'] == "playing":
                self.animationWindow.setAnimation(True)
            self.mainWindow.setState(self.playerState)    
                
                
    def updateBuffer(self, data):
        if('buffer' in data.keys()):
            self.playerState['buffer'] = data['buffer']
            self.bufferWindow.setState(self.playerState)
