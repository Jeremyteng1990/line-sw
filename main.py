# -*- coding: utf-8 -*-
__author__ = 'Sonny'
import ciscolib
import socket
import os
import subprocess
import tkinter
import tkinter.messagebox
import tkinter.font
import tkinter.ttk
from tkinter.ttk import Notebook
import tkinter.filedialog
import ctypes
import re
import codecs
import shutil
import datetime
import base64
import sys

Cmd = [[], []]              # 当前缓存命令
x_to_x_menu_dict = {}       # x_to_x菜单字典
now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
line_switch = None
Dividing = '\n\n' + '--*--' * 13 + '\n\n'
VPN_Link_Common = ['10.8.10.241', '10.8.10.242', '10.8.10.238']
VPN_Link_Extra = ['10.0.0.6']

def Input_Config():
    '读取配置文件并组成列表'
    global Link_Static_Route, Application_Static_Route, Gateway, Login_pwd, Privileged_pwd
    Link_Static_Route, Application_Static_Route = [], []
    gateway_regular = 'Gateway=( )?(\d{1,3}.){3}\d{1,3}\s'
    Login_regular = 'Login_pwd=( )?\S*\s'
    privileged_regular = 'Privileged_pwd=( )?\S*\s'
    vsr_regular = 'VPN_Static_Route=\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*'
    asr_regular = 'Application_Static_Route=\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*'
    pattern = gateway_regular + '|' + Login_regular + '|' + privileged_regular + '|' + vsr_regular + '|' + asr_regular
    # pattern = '\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*|\[.*\]|(\d{1,3}.){3}\d{1,3}'
    # |\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*   匹配无注释
    try:
        configurefile = codecs.open('Config.ini', 'rb', encoding='utf-8')
        for x in configurefile.readlines():
            pattern_re = re.match(pattern, x)
            if pattern_re:
                patstr = pattern_re.group()
                patstr_value = patstr[patstr.index('=')+1:].strip()
                # print(patstr.strip())
                if 'Gateway' in patstr:
                    Gateway = patstr_value
                elif 'Login_pwd' in patstr:
                    Login_pwd = Decrypt(patstr_value)
                elif 'Privileged_pwd' in patstr:
                    Privileged_pwd = Decrypt(patstr_value)
                elif 'VPN_Static_Route' in patstr:
                    Link_Static_Route.append([patstr[patstr.index('=')+1:patstr.index('name')].strip(), patstr[patstr.index('name'):].strip()])
                elif 'Application_Static_Route' in patstr:
                    Application_Static_Route.append([patstr[patstr.index('=')+1:patstr.index('name')].strip(), patstr[patstr.index('name'):].strip()])
                else:
                    print(patstr)
        configurefile.close()
    except Exception as err:
        gui_text.insert('end', Dividing + '读取配置文件失败！\nError Code:%s' % str(err))
        return False
    return True

def Login_Route():
    '检测网关通路 连接到目标， 成功则返回show run'
    ping = subprocess.call("ping -n 2 -w 1 %s" % Gateway, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ping == 1:
        gui_text.insert('end', '无法连接到网关，请检查你的本地网络连接是否正常！\n')
        gui_text.see('end')
        return None, None, False
    switch = ciscolib.Device(Gateway, "%s" % Login_pwd)
    try:
        switch.connect()
    except Exception as err:
        gui_text.insert('end', '无法登录到网关，请确认密码！\nError Code:' + str(err))
        gui_text.see('end')
    else:
        try:
            switch.enable("%s" % Privileged_pwd)
        except Exception as err:
            gui_text.insert('end', Dividing + '未能成功登录特权模式！\nError Code:' + str(err))
        else:
            showrun = str(switch.cmd("show run"))
            switch.cmd('conf t')
            return showrun, switch, True
    return None, None, False

def Detect_Localip():
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception as err:
        # tkinter.messagebox.showerror('错误', str(err))
        gui_text.insert('end', Dividing + '读取本机IP出错！\n' + str(err), '\n')
        return False
    else:
        if ip == '127.0.0.1':
            gui_text.insert('end', Dividing + '无法获得有效的本机IP！\n')
            return False
        elif '192.168.5' in ip or '10.8.' in ip:
            return ip
        else:
            gui_text.insert('end', Dividing + '您的主机没有被授权使用本软件,无法继续操作！\n如在内网连接了VPN请先断开再试！\n')
            return False

def Line_Detction(sh_run, *args):
    '检测当前所在线路'
    Vpn_result = []
    App_result = []
    x = True                    # 二次迭代为application
    for group in args:
        for line in group:
            if line[0] in sh_run:
                a = sh_run.index(line[0]) + len(line[0]) + 1
                b = a + sh_run[a:].index(' ' or '\n')
                c = sh_run[a:b]
                # [name,gw,ip route]
                if x:
                    Vpn_result.append([line[0], c, line[-1]])
                else:
                    App_result.append([line[0], c, line[-1]])
            else:
                if x:
                    Vpn_result.append([line[0], None, line[-1]])
                else:
                    App_result.append([line[0], None, line[-1]])
        x = False
    return [Vpn_result, App_result]

def Link_Group(line_status):
    'readme = [[vpn], [app]]'
    No_Online = []
    line_common = {}
    line_extra = {}
    for x in VPN_Link_Common:
        line_common[x] = [[], []]
    for x in VPN_Link_Extra:
        line_extra[x] = [[], []]
    count = 0
    for group in line_status:
        for line in group:
            if line[1] in VPN_Link_Common:
                line_common[line[1]][count].append([line[0], line[-1]])
            elif line[1] in VPN_Link_Extra:
                line_extra[line[1]][count].append([line[0], line[-1]])
            else:
                No_Online.append(line[0] + ' ' + line[-1])
                print('%s 当前不存在！' % line[0])
        count = 1
    return line_common, line_extra, No_Online


def Link_Switching(options, *args):
    '生成最终路由指令'
    global Cmd
    a, b, c, d = options[0], options[1], options[2], options[3]
    if d:
        xm = False
    else:
        xm = True

    def check_command(command):
        '过滤重复或者肯能产生冲突的命令'
        for x in Cmd:
            for route in x:
                if command in route:
                    gui_text.insert('end', '\n移除重复或冲突缓存:\n' + Cmd[Cmd.index(x)].pop(x.index(route)) + '\n')

    if Cmd != [[], []]:
        gui_text.insert('end', Dividing + '检查命令冲突...\n')

    if a == 1:                                            # 全体切换到241/242
        target_line = b - 1
        for gw in args:
            if args.index(gw) == target_line:
                '''路由条目已在目标网关依然要检测缓存的命令'''
                for check in gw:
                    for check_2 in check:
                        check_command(check_2[0])
                continue
            for group in gw:
                for iproute in group:
                    check_command(iproute[0])
                    Cmd[0].append('no ' + iproute[0] + ' ' + VPN_Link[args.index(gw)])
                    Cmd[1].append(iproute[0] + ' ' + VPN_Link[target_line] + ' ' + iproute[-1])
            if xm:
                break
    elif a == 2:                                          # vpn/app 切换到 241/242
        sources_type = b - 1
        target_line = c - 1
        for gw in args:
            if args.index(gw) == target_line:
                for check in gw[sources_type]:        # 路由条目已在目标网关依然要检测缓存的命令
                    for check_2 in check:
                        check_command(check_2[0])
                continue
            for group in gw[sources_type]:
                check_command(group[0])
                Cmd[0].append('no ' + group[0] + ' ' + VPN_Link[args.index(gw)])
                Cmd[1].append(group[0] + ' ' + VPN_Link[target_line] + ' ' + group[-1])
            if xm:
                break
    elif a == 3:                                        # 位于X的Y切换到Z
        sources_line = b - 1
        if c is 1 or c is 2:
            aa = c - 1
        else:
            aa = 0
        target_line = d - 1
        for gw in args[sources_line][aa:c]:
            for group in gw:
                check_command(group[0])
                Cmd[0].append('no ' + group[0] + ' ' + VPN_Link[sources_line])
                Cmd[1].append(group[0] + ' ' + VPN_Link[target_line] + ' ' + group[-1])

    elif a == 4:                                        # 将线路X 切换到出口Y
        x = True
        global Line_Status
        if Line_Status[b][c][1]:
            check_command(Line_Status[b][c][0])
            Cmd[0].append('no ' + Line_Status[b][c][0] + ' ' + Line_Status[b][c][1])
            x = False
        if d is False:
            return None
        if x:
            check_command(Line_Status[b][c][0])
        Cmd[1].append(Line_Status[b][c][0] + ' ' + VPN_Link[d] + ' ' + Line_Status[b][c][-1])


def Run_Command():
    '执行命令'
    global Line_241, Line_242, Line_XM
    if len(Cmd[0]) == 0 and len(Cmd[1]) == 0:
        gui_text.insert('end', Dividing + '当前无缓存的命令！\n')
    else:
        try:
            for x in Cmd:
                for xx in x:
                    switch_config_t.cmd(xx)
        except Exception as err:
            gui_text.insert('end', '\n执行命令出现错误:\n' + str(err))
        else:
            gui_text.insert('end', Dividing + '命令已执行完毕！')
            Flush_Route_Status(switch_config_t)                     # 刷新状态
            Gui_Line_Switch_Menu(True)                             # 刷新菜单
            Line_241, Line_242, Line_XM = Link_Group(Line_Status)    # 刷新链路组
            Cmd_Clear(False)                                        # 清空命令
    gui_text.see('end')

def Flush_Route_Status(switch_config_t):       # 刷新路由状态
    global Line_Status, sh_run
    try:
        switch_config_t.cmd('end')
        sh_run = str(switch_config_t.cmd('show run'))
        Line_Status = Line_Detction(sh_run, Link_Static_Route, Application_Static_Route)
        switch_config_t.cmd('config t')
    except Exception as err:
        gui_text.insert('end', Dividing + '刷新路由状态失败:\n' + str(err))
    else:
        gui_text.insert('end', Dividing + '路由状态已刷新！')
    gui_text.see('end')


def Exit_Switch():
    try:
        switch_config_t.cmd('end')
        switch_config_t.cmd('exit')
    except Exception as err:
        gui_text.insert('end', Dividing + '与路由断开时出现错误，你可以直接X掉窗口\n' + str(err) + '\n')
        gui_text.see('end')
    finally:
        sys.exit()


def Show_Cmd(args):
    '显示当前缓存的命令'
    text = ['当前缓存的命令如下:\n\n',
            '当前没有缓存命令！\n\n',
            '以下命令已缓存，可以开始执行命令！\n\n',
            '当前没有找到需要操作的内容！\n\n']
    if args:
        text_show = text[2:]
    else:
        text_show = text[:2]
    if Cmd != [[], []]:
        gui_text.insert('end', Dividing + text_show[0])
        for x in Cmd:
            for xx in x:
                gui_text.insert('end', xx+'\n')
    else:
        gui_text.insert('end',  Dividing + text_show[1])
    gui_text.see('end')


def Cmd_Clear(args=True):
    '清除缓存的命令'
    global Cmd
    Cmd = [[], []]
    if args:            # 手动清空
        gui_text.insert('end', Dividing + '已清空！\n')
    gui_text.see('end')


def all_object_menu_box(message, *args):
    '全体对象切换到X --> 切换到241/242网关'
    re = tkinter.messagebox.askyesnocancel(title='额外选项', message='是否包含厦门专线10.0.0.6上的%s ?' % message)
    if re is None:
        pass
    else:
        Link_Switching([args[0], args[1], args[2], re], Line_241, Line_242, Line_XM)
        Show_Cmd(True)


def Input_Command(*args):
        Link_Switching([args[0], args[1], args[2], args[3]], Line_241, Line_242, Line_XM)
        Show_Cmd(True)

def Show_Status():
    '显示当前线路状态'
    gui_text.insert('end', Dividing)
    for x in Line_Status:
        for xx in x:
            gui_text.insert('end', " %-35s链路接口为%18s" % (xx[-1][5:], xx[1]) + '\n' + '-' * 65 + '\n')
    # tab.focus_force() 光标移动至末尾
    gui_text.see('end')          # 滚动条滚动到末尾

def Show_Route_Def():
    '显示路由定义'
    route_len = 0
    name_len = 0
    gui_text.insert('end', Dividing)
    for x in [Link_Static_Route, Application_Static_Route]:
        for xx in x:
            if route_len < len(xx[0]):
                route_len = len(xx[0])
            if name_len < len(xx[1]):
                name_len = len(xx[1])
    for x in [Link_Static_Route, Application_Static_Route]:
        for xx in x:
            gui_text.insert('end', '%-*s %-*s' % (route_len, xx[0], name_len - 5, xx[1][5:]) + '\n' + '-' * 67 + '\n')
    gui_text.see('end')

def Clear_Text():
    '''清空output'''
    gui_text.delete('0.0', 'end')

def Text_input():
    '''print(gui_text.get('0.0', 'end'))'''
    gui_text.insert('end', Dividing + '打印功能还未实现...\n')
    gui_text.see('end')

def Again_Login():
    '重新登录路由'
    global sh_run, switch_config_t, link
    try:
        switch_config_t.disconnect()
    except:
        pass
    try:
        sh_run, switch_config_t, link = Login_Route()
    except NameError as err:
        gui_text.insert('end', Dividing + '此时无法连使用此功能 :(\n' + str(err) + '\n')
    except Exception as err:
        gui_text.insert('end', Dividing + '尝试从新连接失败！\nError Code:%s' % str(err) + '\n')
    if link:
        gui_text.insert('end', Dividing + '已成功重新登录到路由！\n')
    gui_text.see('end')

def Again_Read_Configure():
    '重新读取配置并重新登录目标'
    global Line_Status, Line_241, Line_242, Line_XM, Gateway, switch_config_t, sh_run
    gui_text.insert('end', Dividing)
    try:
        switch_config_t.disconnect()
    except:
        pass
    try:
        Input_Config()                                                                          # 读取配置
        gui_text.insert('end', '尝试重新登录目标...\n')
        sh_run, switch_config_t, status = Login_Route()                                           # 连接目标
        if status:
            Line_Status = Line_Detction(sh_run, Link_Static_Route, Application_Static_Route)        # 刷新线路状态信息
            Line_241, Line_242, Line_XM = Link_Group(Line_Status)                                   # 刷新变量
            Flush_Route_Status(switch_config_t)                                                     # 刷新路由show run
            Gui_Line_Switch_Menu()                                                                  # 刷新菜单
            Gui_Button_Panel(Panel_Status)                                                          # 尝试生成面板
        else:
            gui_text.insert('end', '\n登录失败 :(')
    except BaseException as err:
        gui_text.insert('end', Dividing + '出现错误:\n' + str(err))
    else:
        if status:
            gui_text.insert('end', Dividing + '已重新载入！\n')
    finally:
        gui_text.see('end')

def Decrypt(text):
        '''解密登录密码'''
        text = text[2:-1]
        textbyt = str.encode(text)
        decodestr = base64.b64decode(textbyt)
        pw_byt = decodestr[28:]
        pw = base64.b64decode(pw_byt)
        pw = base64.b64decode(pw)
        decodestr = str(pw, encoding='utf-8')
        return decodestr

class Gui_ChangePassword(tkinter.Frame):
    '绘制修改密码框'
    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.pack()
        self.Login_pwd = tkinter.Entry(self, show='*')
        self.Login_pwd.grid(row=0, column=1, pady=3)
        self.Privileged_pwd = tkinter.Entry(self, show='*')
        self.Privileged_pwd.grid(row=1, column=1, pady=3)

        self.login_lab = tkinter.Label(self, text='登录密码')
        self.login_lab.grid(row=0, column=0, pady=4, padx=3, sticky='w')
        self.Privileged_lab = tkinter.Label(self, text='特权密码')
        self.Privileged_lab.grid(row=1, column=0, pady=4, padx=3, sticky='w')

        self.login_re = tkinter.StringVar()
        self.Login_pwd.config(textvariable=self.login_re)
        # self.contents.set("this is a variable")
        # self.Login_pwd.bind('<Key-Return>', self.print_contents)

        self.Privileged_pwd_re = tkinter.StringVar()
        self.Privileged_pwd.config(textvariable=self.Privileged_pwd_re)

        self.button = tkinter.Button(self, text="确定", width=6, command=self.Encrypted)
        self.button.grid(row=2, column=0, pady=5, padx=30, sticky='w', columnspan=2)
        self.button_2 = tkinter.Button(self, text="取消", width=6, command=lambda: self.destroy())
        self.button_2.grid(row=2, column=1, pady=5, padx=30, columnspan=2, sticky='e')

    # def upper(self):
    #     str = self.login_re.get().upper()
    #     self.login_re.set(str)
    #     print('the contents is : ', self.login_re.get())
    #     # self.destroy()
    #
    # def print_contents(self, event):
    #     print("hi. contents of entry is now ---->", self.login_re.get())

    def Encrypted(self):
        '简单加密字符串'
        if self.login_re.get() == '' and self.Privileged_pwd_re.get() == '':
            gui_text.insert('end', Dividing + '输入不能为空！\n')
            gui_text.see('end')
            return None
        key = b'ishshntiszishshishizd'
        enkey = base64.b64encode(key)
        login_byt = str.encode(self.login_re.get())
        Privileged_byt = str.encode(self.Privileged_pwd_re.get())

        enlogin = base64.b64encode(login_byt)
        enprivileged = base64.b64encode(Privileged_byt)
        enlogin = base64.b64encode(enlogin)
        enprivileged = base64.b64encode(enprivileged)

        enlogin = enkey + enlogin
        enprivileged = enkey + enprivileged

        self.en_login_save = base64.b64encode(enlogin)
        self.enprivileged_save = base64.b64encode(enprivileged)

        self.SaveFile()

    def SaveFile(self):
        '向文件写入输入的密码'
        try:
            fileopen = open('Config.ini', 'r', encoding='utf-8')
            files = fileopen.readlines()
            fileopen.close()
        except BaseException as err:
            gui_text.insert('end', '无法打开配置文件，未能成功修改！\n' + str(err))
        else:
            try:
                '''备份副本并打开文件'''
                shutil.copyfile('Config.ini', 'Config.ini.bak')
                fileopen = open('Config.ini', 'w', encoding='utf-8')
                for x in files:
                    if 'Login_pwd' in x and self.login_re.get() != '':
                        files[files.index(x)] = 'Login_pwd=%s\n' % str(self.en_login_save)
                    if 'Privileged_pwd' in x and self.Privileged_pwd_re.get() != '':
                        files[files.index(x)] = 'Privileged_pwd=%s\n' % str(self.enprivileged_save)
                fileopen.writelines(files)
                gui_text.insert('end', Dividing + '已修改！\n')
            except BaseException as err:
                gui_text.insert('end', '无法写入配置文件！\n' + str(err))
            else:
                os.remove('Config.ini.bak')
            fileopen.close()
        gui_text.see('end')
        self.destroy()

def Gui_System_Menu():
    '生成主菜单栏'
    filemenu = tkinter.Menu(Menu_bar, tearoff=0, font=ch_font)
    # filemenu.add_command(label='Open')
    filemenu.add_command(label='重新登录到路由', command=Again_Login)
    filemenu.add_command(label='重新读取配置文件', command=Again_Read_Configure)
    filemenu.add_command(label='修改连接密码', command=lambda: Gui_ChangePassword(root))
    filemenu.add_separator()
    filemenu.add_command(label='保存日志窗口', command=lambda: save_text(gui_text.get('0.0', 'end'), **save_options))
    # filemenu.add_command(label='打印日志窗口', command=Text_input)
    filemenu.add_command(label='清空消息窗口', command=Clear_Text)
    filemenu.add_separator()
    filemenu.add_command(label=' 退出 ', command=lambda: sys.exit())
    Menu_bar.add_cascade(label=' 系统 ', menu=filemenu, font=ch_font)
    save_options = {}
    save_options['defaultextension'] = '.txt'
    save_options['filetypes'] = [('text files', '.txt'), ('all files', '.*')]
    save_options['initialdir'] = 'C:\\'
    save_options['initialfile'] = 'input.txt'
    save_options['parent'] = root
    save_options['title'] = '保存输出'

    def save_text(txt, **args):
        try:
            save = tkinter.filedialog.asksaveasfile(mode='w', **args)
            save.write(txt)
            save.close()
        except Exception:
            gui_text.insert('end', Dividing + '未能成功保存！\n')
            gui_text.see('end')



def Gui_Line_Switch_Menu(*args):
    '生成/更新链路切换菜单'
    global line_switch
    if line_switch:
        line_switch.delete(0, 'end')
    else:
        line_switch = tkinter.Menu(Menu_bar, tearoff=0, font=ch_font)
        Menu_bar.add_cascade(label='线路切换', menu=line_switch)
    # line_switch.add_command(label='全体对象切换到X')
    all_object_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体对象切换到X', menu=all_object_menu, font=ch_font)
    all_object_menu.add_command(label='-->241网关', command=lambda: all_object_menu_box('对象', 1, 1, None))
    all_object_menu.add_command(label='-->242网关', command=lambda: all_object_menu_box('对象', 1, 2, None))

    all_vpn_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体VPN切换到X', menu=all_vpn_menu, font=ch_font)
    all_vpn_menu.add_command(label='-->241网关', command=lambda: all_object_menu_box('VPN线路', 2, 1, 1))
    all_vpn_menu.add_command(label='-->242网关', command=lambda: all_object_menu_box('VPN线路', 2, 1, 2))

    all_app_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体APP切换到X', menu=all_app_menu, font=ch_font)
    all_app_menu.add_command(label='-->241网关', command=lambda: all_object_menu_box('APP线路', 2, 2, 1))
    all_app_menu.add_command(label='-->242网关', command=lambda: all_object_menu_box('APP线路', 2, 2, 2))
    line_switch.add_separator()
    # -----------------------------------------------------------------------------------------------------
    line_to_x_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='位于线路X的VPN/APP切换到Y', menu=line_to_x_menu, font=ch_font)

    line_241 = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font)
    line_to_x_menu.add_cascade(label='位于线路241', menu=line_241, font=ch_font)
    vpn_line_1 = tkinter.Menu(line_241, tearoff=0, font=ch_font)
    app_line_1 = tkinter.Menu(line_241, tearoff=0, font=ch_font)
    all_line_1 = tkinter.Menu(line_241, tearoff=0, font=ch_font)
    line_241.add_cascade(label='的VPN', menu=vpn_line_1, font=ch_font)
    line_241.add_cascade(label='的App', menu=app_line_1, font=ch_font)
    line_241.add_cascade(label='的所有路由', menu=all_line_1, font=ch_font)
    vpn_line_1.add_command(label='切换到242', command=lambda: Input_Command(3, 1, 1, 2))       # 将位于241的VPN路由切换到242
    app_line_1.add_command(label='切换到242', command=lambda: Input_Command(3, 1, 2, 2))       # 将位于241的app路由切换到242
    all_line_1.add_command(label='切换到242', command=lambda: Input_Command(3, 1, 3, 2))       # 将位于241的所有路由切换到242

    line_242 = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font)
    line_to_x_menu.add_cascade(label='位于线路242', menu=line_242, font=ch_font)
    vpn_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    app_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    all_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    vpn_line_2.add_command(label='切换到241', command=lambda: Input_Command(3, 2, 1, 1))
    app_line_2.add_command(label='切换到241', command=lambda: Input_Command(3, 2, 2, 1))
    all_line_2.add_command(label='切换到241', command=lambda: Input_Command(3, 2, 3, 1))
    line_242.add_cascade(label='的VPN', menu=vpn_line_2, font=ch_font)
    line_242.add_cascade(label='的APP', menu=app_line_2, font=ch_font)
    line_242.add_cascade(label='的所有路由', menu=all_line_2, font=ch_font)

    line_xm = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font)
    line_to_x_menu.add_cascade(label='位于线路0.6', menu=line_xm, font=ch_font)
    xm_line = tkinter.Menu(line_xm, tearoff=0, font=ch_font)
    line_xm.add_cascade(label='的VPN链路', menu=xm_line, font=ch_font)
    xm_line.add_command(label='切换到241', command=lambda: Input_Command(3, 3, 1, 1))
    xm_line.add_command(label='切换到242', command=lambda: Input_Command(3, 3, 1, 2))
    line_switch.add_separator()
    # --------------------------------------------------------------------------------------------------
    x_to_x = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='将X路由切换到线路Y', menu=x_to_x, font=ch_font)
    global x_to_x_menu_dict          # 存储动态变量
    separator = True
    if x_to_x_menu_dict:
        for y in x_to_x_menu_dict.items():
            y[1].delete('0', 'end')
        gui_text.insert('end', Dividing + '菜单已刷新！\n')
        gui_text.see('end')
    for x1 in Line_Status:
        for x2 in x1:
            x_to_x_menu_dict[x2[-1][5:]] = tkinter.Menu(x_to_x, tearoff=0, font=ch_font)
            x_to_x.add_cascade(label=x2[-1][5:], menu=x_to_x_menu_dict[x2[-1][5:]], font=ch_font)
            if x2[1] in VPN_Link:
                str = '切换到'
            else:
                 str = '添加到'
            for x3 in VPN_Link:
                if x2[1] != x3:
                    # command=lambda x3=x3 , x1=x1, x2=x2: Input_Command   创建当前循环的快照
                    x_to_x_menu_dict[x2[-1][5:]].add_command(label='%s%s' % (str, x3), command=lambda x3=x3 , x1=x1, x2=x2: Input_Command(4, Line_Status.index(x1), x1.index(x2), VPN_Link.index(x3)))
            if x2[1] in VPN_Link:
                x_to_x_menu_dict[x2[-1][5:]].add_command(label='从路由表删除', command=lambda x1=x1, x2=x2: Input_Command(4, Line_Status.index(x1), x1.index(x2), False))
        if separator:
            x_to_x.add_separator()
            separator = False


def Gui_Button_Panel(Status):
    '生成按钮面板'
    # 首先检查是否已经生成过
    if Status:
        OptionsMenu = tkinter.Frame(button_frame, width=500, height=120, bg='#FFFAFA')
        OptionsMenu.propagate(False)
        OptionsMenu.pack(side='bottom')
        # boxinfo = tkinter.messagebox.showinfo('标题1', 'this 按钮1')
        grid = {'padx': 8, 'pady': 4, 'sticky': 'ewns'}
        tkinter.Button(OptionsMenu, text='显示当前线路状态', width=17, command=Show_Status).grid(row=0, column=0, **grid)
        tkinter.Button(OptionsMenu, text='显示路由定义', width=17, command=Show_Route_Def).grid(row=0, column=1, **grid)
        tkinter.Button(OptionsMenu, text='清空已缓存的命令', width=17, command=Cmd_Clear).grid(row=0, column=2,  **grid)

        tkinter.Button(OptionsMenu, text='刷新菜单', width=17, command=lambda: Gui_Line_Switch_Menu(True)).grid(row=1, column=0, **grid)
        tkinter.Button(OptionsMenu, text='刷新路由状态', width=17, command=lambda: Flush_Route_Status(switch_config_t)).grid(row=1, column=1, **grid)
        tkinter.Button(OptionsMenu, text='查看已缓存的命令', width=17, command=lambda: Show_Cmd(False)).grid(row=1, column=2,  **grid)

        tkinter.Button(OptionsMenu, text='清空输出信息', width=17, command=Clear_Text).grid(row=2, column=0,  **grid)
        tkinter.Button(OptionsMenu, text='登出路由并离开', width=17, command=Exit_Switch).grid(row=2, column=1,  **grid)
        tkinter.Button(OptionsMenu, text='执行命令！', command=Run_Command, width=17, bg='#87CEEB').grid(row=2, column=2,  **grid)
        # tkinter.Button(OptionsMenu, text='读取配置文件', width=17=23, command=Input_Config).grid(row=2, column=0, padx=1, pady=2)
    return False


def Gui_Root_Frame():
    '''初始化ROOT窗口并创建主要Frame'''
    # 获取当前分辨率
    user32 = ctypes.windll.user32
    screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    # GUI框架
    root = tkinter.Tk()
    # root.geometry('500x600+%d+%d' % (screensize[0]//2 - 250, screensize[1]//2 - 300))
    root.title('Fast Route Switch ')
    root.resizable(width=False, height=True)
    # top_info_frame = tkinter.Frame(root, width=500, height=30, bg='green')
    # top_info_frame.propagate(False)
    # # top_info_frame.pack()
    button_frame = tkinter.Frame(root, width=500, height=145, bg='#FFFAFA')
    button_frame.propagate(False)
    button_frame.pack()
    en_font = tkinter.font.Font(family='Arial', size=10, weight='normal')
    ch_font = tkinter.font.Font(family='Microsoft YaHei', size=10, weight='normal')
    tkinter.Label(root, text='Output Info:', font=en_font, bg='white').pack(fill='x', anchor='w')
    info_frame = tkinter.Frame(root, width=500, height=400, bg='#d5d2d2')                           # 输出文本之框架
    info_frame.propagate(False)
    info_frame.pack()
    return root, button_frame, info_frame, en_font, ch_font, screensize

def Gui_Text_Frame():
    '绘制文本框架'
    gui_text = tkinter.Text(info_frame, width=68, height=30,  bg='#494848', fg='#C3C3C3')
    gui_text.bind("<BackSpace>", lambda e: "break")         # 忽略退格键
    # gui_text.bind("<KeyPress>", lambda e: "break")            # 忽略所以键
    # gui_text['state'] = 'normal'                           # 文本框读写属性
    gui_text.pack(side='left')      # , fill='y'

    scrollbar = tkinter.ttk.Scrollbar(info_frame, orient='vertical', command=gui_text.yview)
    scrollbar.pack(side='right', fill='y')
    gui_text['yscrollcommand'] = scrollbar.set
    return gui_text

def Gui_Help_Menu():
    '生成帮助菜单'
    help_menu = tkinter.Menu(Menu_bar, tearoff=0, font=ch_font)
    Menu_bar.add_cascade(label='  帮助  ', menu=help_menu, font=ch_font)

    def about_frame():
        about = tkinter.Tk()
        about.geometry('280x345+%d+%d' % (screensize[0]//2 - 140, screensize[1]//2 - 170))
        about.resizable(width=False, height=False)
        about.title('关于')
        about.propagate(False)
        about_text_frame = tkinter.Frame(about, width=270, height=310, bg='#696969')
        about_text_frame.propagate(False)
        about_text_frame.pack(side='top')
        about_close = tkinter.Button(about, text='关闭', width=12, command=lambda: about.destroy())
        about_close.pack(anchor='s')
        # about.configure(background='#696969')
        # about_text = tkinter.Text(about, font=('Microsoft YaHei', 8), width=210, height=290, bg='#696969', fg='#fffafa')
        # about_text.bind("<KeyPress>", lambda e: "break")
        # about_text.pack()
        # about_text.insert('end', '\n\n\n            Fast Switch Route\n      一个用Python和Tkinter写的小工具')
        tkinter.Label(about_text_frame, text='\nFast Route Switch', fg='#fffafa', bg='#696969', font=('Helvetica', 15, 'bold')).pack(anchor='nw')
        tkinter.Label(about_text_frame, text='V0.1 ISH专用', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 9)).pack(anchor='nw')
        tkinter.Label(about_text_frame, text='\n一个用Python和Tkinter写的Cisco路由表切换工具\n'
                                             '如遇到bug或异常请发送邮件给作者.', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='w')
        tkinter.Label(about_text_frame, text='%s' % '\n'*6, fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')
        tkinter.Label(about_text_frame, text='build:2015-10-20 16:40:59', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')
        tkinter.Label(about_text_frame, text='Developer:Sonny Yang', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')
        tkinter.Label(about_text_frame, text='Email:klzsysy@live.com; it_yangsy@ish.com.cn', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')

    def readme_frame():
        readme = tkinter.Tk()
        readme.resizable(width=False, height=False)
        readme.title('定义说明')
        readme.propagate(False)
        readme.geometry('510x316+%d+%d' % (screensize[0]//2 - 140, screensize[1]//2 - 170))
        readme_text = tkinter.Text(readme, width=62, height=14,  bg='#494848', fg='#C3C3C3', font=('Microsoft YaHei', 10))
        readme_text.propagate(False)
        readme_text.pack()
        readme_text.bind("<BackSpace>", lambda e: "break")
        readme_text.insert('end', '<线路切换>菜单中的<全体对象>是指在配置文件中已定义且在路由运行的路由，点击<显示当前线路状态>即可查看配置文件中定义路由的运行状态.\n')
        readme_text.insert('end', '\n全体VPN是指在配置文件中<VPN_Static_Route>所对应的所有路由,\n\n全体APP指的是配置文件中<Application_Static_Route>所有对应的路由.\n')
        readme_text.insert('end', '\n所有路由操作只有在点击执行命令之后才会实际操作路由器.\n\n修改连接密码是指本工具连接到路由的密码，而非修改路由器的密码.\n')
        readme_text.insert('end', '\n菜单中的<将X路由切换到线路Y>适用于操作单条路由表,菜单会在执行命令后自动刷新\n')
        readme_text.insert('end', '\n菜单中的241, 242, 0.6 分别对应10.8.10.241, 10.8.10.242, 10.0.0.6')
        tkinter.Button(readme, text='大概看懂了', width=12, command=lambda: readme.destroy()).pack(side='bottom', pady=5)

    help_menu.add_command(label='说明', command=readme_frame)
    help_menu.add_command(label='关于', command=about_frame)

def Gui_Menu_Bar():
    '''生成菜单栏'''
    Menubar = tkinter.Menu(root, font=ch_font, bg='red')
    root.config(menu=Menubar)
    return Menubar

if __name__ == '__main__':
    Panel_Status = True
    root, button_frame, info_frame, en_font, ch_font, screensize = Gui_Root_Frame()         # 构建主窗口
    gui_text = Gui_Text_Frame()                                                             # 生成log框
    Menu_bar = Gui_Menu_Bar()                                                               # 生成菜单栏
    Gui_System_Menu()                                                                       # 生成系统菜单
    if Input_Config():
        if Detect_Localip():                                                                # 检查本机IP与授权
            sh_run, switch_config_t, link = Login_Route()                                   # 登录目标
            if link:
                Line_Status = Line_Detction(sh_run, Link_Static_Route, Application_Static_Route)
                Line_Common, Line_Extra, No_Online = Link_Group(Line_Status)
                Gui_Line_Switch_Menu()                                                      # 生成链路切换菜单
                Panel_Status = Gui_Button_Panel(Panel_Status)                               # 生成按钮面板
                gui_text.insert('end', '\nHello World！\n')
            else:
                gui_text.insert('end', '\n\n连接路由器失败 :(\n')
    Gui_Help_Menu()                                                                         # 生成帮助菜单
    root.mainloop()                                                                         # 启动循环

    # nb = Notebook(info, height = 240,width=480)
    # tab = tkinter.Text(nb)
    # nb.add(tab, text='log')
    # nb.pack()
    # box2 = tkinter.Listbox(info, width=68)
    # box2.pack(side='left', fill='y')
    # box = tkinter.Message(SystemMenu,text='message' * 20,width=390,bg='red')
    # box.pack(anchor='nw')
