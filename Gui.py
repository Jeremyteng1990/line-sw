__author__ = 'yangsiyi'
from tkinter import  *
import tkinter.messagebox as messagebox

class test(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

    def createWidgets(self):
        self.helloLabel = Label(self, text='Hello, world!')
        self.oneButton = Button(self, text='exit', command=self.quit)
        self.oneButton.pack()
        self.towButton = Button(self, text='tow', command=self.hello)
        self.towButton.pack()
        self.name = Entry(self)
        self.name.pack()
        self.helloLabel.pack()
        self.threeButton = Button(self, text='返回‘1’', command=self.hello)

    def result1(self):
        return '1'

    def hello(self):
        namein = self.name.get() or 'sonny'
        messagebox.showinfo('弹出标题', 'hello %s' % namein)

app = test()
app.master.geometry('300x300')
app.master.title('Hello World')
app.mainloop()

