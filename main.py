# -*- coding: utf-8 -*-
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
import configparser

__author__ = 'Sonny'
Cmd = [[], []]              # 当前缓存命令
now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
line_switch = None
x_to_x_dict = {}
Dividing = '\n' + '--*--' * 13 + '\n\n'


def input_config():
    '读取配置文件并组成列表'
    global Link_Static_Route, Application_Static_Route, Gateway_Total, Connect_Config
    Link_Static_Route, Application_Static_Route = [], []
    Gateway_Total = {'VPN_Link_Common': [], 'VPN_Link_Extra': []}
    Connect_Config = {}
    gateway_regular = 'Gateway=( )?(\d{1,3}.){3}\d{1,3}\s'
    login_regular = 'Login_pwd=( )?\S*\s'
    vpn_link_common_regular = 'VPN_Link_Common\s*=\s*((2[0-4]\d|25[0-5]|[01]?\d\d?).){3}(2[0-4]\d|25[0-5]|[01]?\d\d?)'
    privileged_regular = 'Privileged_pwd\s*=( )?\S*\s'
    vsr_regular = 'VPN_Static_Route\s*=\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*'
    asr_regular = 'Application_Static_Route\s*=\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*'
    pattern = gateway_regular + '|' + login_regular + '|' + privileged_regular + '|' + vsr_regular + '|' + asr_regular
    # pattern = '\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*name*.*|\[.*\]|(\d{1,3}.){3}\d{1,3}'
    # |\s*ip\s+route\s+(\d{1,3}.){3}\d{1,3}\s+(\d{1,3}.){3}\d{1,3}\s*   匹配无注释
    try:
        configurefile = codecs.open('Config.ini', 'rb', encoding='utf-8')
        for x in configurefile.readlines():
            pattern_re = re.match(pattern, x)
            if pattern_re:
                patstr = pattern_re.group()
                patstr_value = patstr[patstr.index('=')+1:].strip()
                if 'Route' in patstr:
                    Connect_Config['Route'] = patstr_value
                elif 'Login_pwd' in patstr:
                    Connect_Config['Login_pwd'] = decrypt(patstr_value)
                elif 'Privileged_pwd' in patstr:
                    Connect_Config['Privileged_pwd'] = decrypt(patstr_value)
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


def read_config():
    global Link_Static_Route, Application_Static_Route, Connect_Config, Gateway_Total
    Link_Static_Route, Application_Static_Route = [], []
    Gateway_Total = {'VPN_Link_Common': [], 'VPN_Link_Extra': []}
    Connect_Config = {}
    re_ip = '((2[0-4]\d|25[0-5]|[01]?\d\d?).){3}(2[0-4]\d|25[0-5]|[01]?\d\d{0,2})'
    route_ip = '((2[0-4]\d|25[0-5]|[01]?\d\d?).){3}(2[0-4]\d|25[0-5]|[01]?\d\d?)\s+'
    re_route = 'ip\s+route\s+%s%sname\s+\S+' % (route_ip, route_ip)
    prog = re.compile(re_ip)
    re_route_compile = re.compile(re_route)

    config = configparser.ConfigParser()        # 创建对象
    config.optionxform = str                    # 保持大小写 需要在读取文件之前
    try:
        config.read("config.ini", encoding='utf-8')
        all_sections = config.sections()            # 获取所有段落字符串
        for sections in all_sections:
            options = config.options(sections)       # 获取sections段落的所有选项字符串
            for x in options:                       # x 每个选项
                value = config.get(sections, x)
                if sections == 'VPN_Static_Route' or sections == 'Application_Static_Route':
                    route = re_route_compile.match(value)
                    if route:
                        value = route.group()
                        if sections == 'VPN_Static_Route':
                            Link_Static_Route.append([value[:value.index('name')].strip(), value[value.index('name'):].strip()])
                        else:
                            Application_Static_Route.append([value[:value.index('name')].strip(), value[value.index('name'):].strip()])
                elif sections == 'Gateway_Config':
                    ip_str = config.get(sections, x)
                    for xx in prog.finditer(ip_str):        # 正则匹配所有IP
                        Gateway_Total[x].append(xx.group().strip())
                        if x == 'VPN_Link_Extra':
                            Gateway_Total['VPN_Link_Common'].append(xx.group().strip())
                elif sections == 'Connect_Config':
                    Connect_Config[x] = config.get(sections, x)
    except Exception as err:
        gui_text.insert('end', Dividing + '读取配置文件出现错误!\n' + str(err))
        gui_text.see('end')
        return False
    else:
        Connect_Config['Login_pwd'] = decrypt(Connect_Config['Login_pwd'])
        Connect_Config['Privileged_pwd'] = decrypt(Connect_Config['Privileged_pwd'])
        return True


def login_route(connect_config):
    '检测网关通路 连接到目标， 成功则返回show run'
    if connect_config['Route'] is None:
        gui_change_password()
    ping = subprocess.call("ping -n 2 -w 1 %s" % connect_config['Route'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ping == 1:
        gui_text.insert('end', '无法连接到网关，请检查你的本地网络连接是否正常！\n')
        gui_text.see('end')
        return None, None, False
    switch = ciscolib.Device(connect_config['Route'], "%s" % connect_config['Login_pwd'])
    try:
        switch.connect()
    except Exception as err:
        gui_text.insert('end', '无法登录到网关，请确认密码！\nError Code:' + str(err))
        gui_text.see('end')
    else:
        try:
            switch.enable("%s" % connect_config['Privileged_pwd'])
        except Exception as err:
            gui_text.insert('end', Dividing + '未能成功登录特权模式！\nError Code:' + str(err))
        else:
            showrun = str(switch.cmd("show run"))
            switch.cmd('conf t')
            return showrun, switch, True
    return None, None, False


def detect_local_ip():
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
        elif '192.168.5' in ip or '10.8.' in ip or '192.168.10' in ip:
            return ip
        else:
            gui_text.insert('end', Dividing + '您的主机没有被授权使用本软件,无法继续操作！\n\n请检查如下操作:\n'
                                              '1.在内网连接了VPN请先断开再试！\n2.检查是否有虚拟网卡\n'
                                              '\n授权的网段：深圳ISH 5网段与深圳服务器网段')
            return False


def line_detction(sh_run, *args):
    '检测当前所在线路'
    Vpn_result = []
    App_result = []
    x = True                    # 二次迭代为application
    for group in args:
        for line in group:
            if line[0] in sh_run:
                a = sh_run.index(line[0]) + len(line[0]) + 1
                b = a + sh_run[a:].index(' ' or '\n')
                c = sh_run[a:b].strip()
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


def link_group(line_status):
    'readme = [[vpn], [app]]'
    no_online = {}
    line_common = {}
    for x in Gateway_Total['VPN_Link_Common']:
        line_common[x] = [[], []]
    count = 0
    for group in line_status:
        for line in group:
            if line[1] in Gateway_Total['VPN_Link_Common']:
                line_common[line[1]][count].append([line[0], line[1], line[-1]])
            else:
                no_online[line[1]] = [line[0], line[1], line[-1]]
                print('路由 %s 未能与Gateway_Config下的IP匹配,表示路由器没有运行这条路由' % line[0])
        count = 1
    return line_common, no_online


def link_switching(options, res, line_set, No_Online):
    '生成最终路由指令'
    global Cmd
    a, b, c, d = options[0], options[1], options[2], options[3]

    def check_command(command):
        '过滤重复或者肯能产生冲突的命令'
        if Cmd != [[], []]:
            for x in Cmd:
                for route in x:
                    if command in route:
                        gui_text.insert('end', '\n移除重复或冲突缓存:\n' + Cmd[Cmd.index(x)].pop(x.index(route)) + '\n')

    def build_command(sources, target=None):
        if not res.get(sources[1], True):                                # 判断是否排除
            return None
        check_command(sources[0])                                        # 检查命令重复或冲突
        # 如果当前路由的下一跳不是要切换的目标 也不为空 同时target也不为空
        if sources[1] != target and sources[1] is not None and target is not None:
            Cmd[0].append('no ' + sources[0] + ' ' + sources[1])
            Cmd[1].append(sources[0] + ' ' + target + ' ' + sources[-1])
        elif sources[1] is None:
            Cmd[1].append(sources[0] + ' ' + target + ' ' + sources[-1])
        elif target is None:
            Cmd[0].append('no ' + sources[0] + ' ' + sources[1])

    if a == 1:
        for x in Line_Status:
            for xx in x:
                build_command(xx, b)
    elif a == 2:                                          # vpn/app 切换到 241/242
        for x in Line_Status[b]:
            build_command(x, c)
    elif a == 3:                                        # 位于X的Y切换到Z
        if c < 2:
            for x in line_set[b][c]:
                build_command(x, d)
        else:
            for x in line_set[b]:
                for xx in x:
                    build_command(xx, d)
    elif a == 4:                                        # 将线路X 切换到出口Y
        if d is True:
            build_command(Line_Status[b][c])
        else:
            build_command(Line_Status[b][c], target=d)


def run_command():
    '执行命令'
    global Line_Set, No_Online
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
            flush_route_status(switch_config_t)                     # 刷新状态
            gui_line_switch_menu(True)                             # 刷新菜单
            Line_Set, No_Online = link_group(Line_Status)           # 刷新链路组
            cmd_clear(False)                                        # 清空命令
    gui_text.see('end')


def flush_route_status(switch_config_t):       # 刷新路由状态
    global Line_Status, sh_run
    try:
        switch_config_t.cmd('end')
        sh_run = str(switch_config_t.cmd('show run'))
        Line_Status = line_detction(sh_run, Link_Static_Route, Application_Static_Route)
        switch_config_t.cmd('config t')
    except Exception as err:
        gui_text.insert('end', Dividing + '刷新路由状态失败:\n' + str(err))
    else:
        gui_text.insert('end', Dividing + '路由状态已刷新！')
    gui_text.see('end')


def exit_switch():
    try:
        switch_config_t.cmd('end')
        switch_config_t.cmd('exit')
    except Exception as err:
        gui_text.insert('end', Dividing + '与路由断开时出现错误，你可以直接X掉窗口\n' + str(err) + '\n')
        gui_text.see('end')
    finally:
        sys.exit()


def show_cmd(args):
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
        gui_text.insert('end', Dividing)
    else:
        gui_text.insert('end',  Dividing + text_show[1])
    gui_text.see('end')


def cmd_clear(args=True):
    '清除缓存的命令'
    global Cmd
    Cmd = [[], []]
    if args:            # 手动清空
        gui_text.insert('end', Dividing + '已清空！\n')
    gui_text.see('end')


def input_command(*args, message=None):
    '组合参数'
    res = {}
    if args[0] < 3:
        for x in Gateway_Total['VPN_Link_Extra']:
            res[x] = tkinter.messagebox.askyesnocancel(title='额外选项', message='是否包含线路%s上的%s ?' % (x, message))
            if res[x] is None:
                return None
    link_switching(args, res, Line_Set, No_Online)
    show_cmd(True)


def show_status():
    '显示当前线路状态'
    gui_text.insert('end', Dividing)
    for x in Line_Status:
        for xx in x:
            gui_text.insert('end', " %-40s链路接口为%14s" % (xx[-1][5:], xx[1]) + '\n' + '-' * 65 + '\n')
    # tab.focus_force() 光标移动至末尾
    gui_text.see('end')          # 滚动条滚动到末尾


def show_route_def():
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

def clear_text():
    '清空output'
    gui_text.delete('0.0', 'end')


def text_input():
    '''print(gui_text.get('0.0', 'end'))'''
    gui_text.insert('end', Dividing + '打印功能还未实现...\n')
    gui_text.see('end')


def again_login():
    '重新登录路由'
    global sh_run, switch_config_t, link, Connect_Config, Panel_Status, Switch_Menu_Status, Line_Status, Line_Set, No_Online
    try:
        switch_config_t.disconnect()
    except:
        pass
    sh_run, switch_config_t, link = login_route(Connect_Config)
    if link:
        try:
            if Panel_Status:
                Panel_Status = gui_button_panel(Panel_Status)
            if Switch_Menu_Status:
                Line_Status = line_detction(sh_run, Link_Static_Route, Application_Static_Route)        # 刷新线路状态信息
                Line_Set, No_Online = link_group(Line_Status)
                Switch_Menu_Status = gui_line_switch_menu()
        except NameError as err:
            gui_text.insert('end', Dividing + '此时无法连使用此功能 :(\n' + str(err) + '\n')
        except Exception as err:
            gui_text.insert('end', Dividing + '尝试从新连接失败！\nError Code:%s' % str(err) + '\n')
        if link:
            gui_text.insert('end', Dividing + '已成功重新登录到路由！\n')
        gui_text.see('end')
    else:
        gui_text.insert('end', Dividing + '尝试从新连接失败！\n')
        gui_text.see('end')


def again_read_configure():
    '重新读取配置并重新登录目标'
    global Line_Status, Line_Set, No_Online, Connect_Config, switch_config_t, sh_run
    gui_text.insert('end', Dividing)
    try:
        switch_config_t.disconnect()
    except:
        pass
    if read_config():
        gui_text.insert('end', '尝试重新登录目标...\n')
        sh_run, switch_config_t, status = login_route(Connect_Config)                                           # 连接目标
        if status:
            Line_Status = line_detction(sh_run, Link_Static_Route, Application_Static_Route)        # 刷新线路状态信息
            Line_Set, No_Online = link_group(Line_Status)                                           # 刷新变量
            flush_route_status(switch_config_t)                                                     # 刷新路由show run
            gui_line_switch_menu()                                                                  # 刷新菜单
            gui_button_panel(Panel_Status)                                                          # 尝试生成面板
        else:
            gui_text.insert('end', '\n登录失败 :(')
        gui_text.see('end')


def decrypt(text):
        '''解密登录密码'''
        text = text[3:-2]
        textbyt = str.encode(text)
        decodestr = base64.b64decode(textbyt)
        pw_byt = decodestr[28:]
        pw = base64.b64decode(pw_byt)
        pw = base64.b64decode(pw)
        decodestr = str(pw, encoding='utf-8')
        return decodestr


class gui_change_password(tkinter.Frame):
    '绘制修改密码框'
    def __init__(self, master):
        tkinter.Frame.__init__(self, master)

        # self.master.geometry('300x200+%d+%d' % (screensize[0]//2 - 150, screensize[1]//2 - 100))
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

        self.button = tkinter.Button(self, text="确定", width=6, command=self.encrypted)
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

    def encrypted(self):
        '简单加密字符串'
        if self.login_re.get() == '' or self.Privileged_pwd_re.get() == '':
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

        self.save_file()

    def save_file(self):
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
                        files[files.index(x)] = 'Login_pwd=[%s]\n' % str(self.en_login_save)
                    if 'Privileged_pwd' in x and self.Privileged_pwd_re.get() != '':
                        files[files.index(x)] = 'Privileged_pwd=[%s]\n' % str(self.enprivileged_save)
                fileopen.writelines(files)
                gui_text.insert('end', Dividing + '已修改！\n')
            except BaseException as err:
                gui_text.insert('end', '无法写入配置文件！\n' + str(err))
            else:
                os.remove('Config.ini.bak')
            fileopen.close()
        gui_text.see('end')
        self.destroy()


def gui_system_menu():
    '生成主菜单栏'
    filemenu = tkinter.Menu(Menu_bar, tearoff=0, font=ch_font)
    # filemenu.add_command(label='Open')
    filemenu.add_command(label='重新登录到路由', command=again_login)
    filemenu.add_command(label='重新读取配置文件', command=again_read_configure)
    filemenu.add_command(label='修改连接密码', command=lambda: gui_change_password(root))
    filemenu.add_separator()
    filemenu.add_command(label='保存日志窗口', command=lambda: save_text(gui_text.get('0.0', 'end'), **save_options))
    # filemenu.add_command(label='打印日志窗口', command=Text_input)
    filemenu.add_command(label='清空消息窗口', command=clear_text)
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


def gui_line_switch_menu(*args):
    '生成/更新链路切换菜单'
    global line_switch
    global x_to_x_dict
    if line_switch:
        line_switch.delete(0, 'end')
    else:
        line_switch = tkinter.Menu(Menu_bar, tearoff=0, font=ch_font)
        Menu_bar.add_cascade(label='线路切换', menu=line_switch)
        # line_switch.add_command(label='全体对象切换到X')
    all_object_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体对象切换到X', menu=all_object_menu, font=ch_font)

    all_vpn_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体VPN切换到X', menu=all_vpn_menu, font=ch_font)

    all_app_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='全体APP切换到X', menu=all_app_menu, font=ch_font)

    for x in Gateway_Total['VPN_Link_Common']:
        # x = x
        if x in Gateway_Total['VPN_Link_Extra']:
            continue
        all_object_menu.add_command(label='%s网关' % x, command=lambda x=x: input_command(1, x, None, None, message='对象'))
        # （type,target,None, message)
        all_vpn_menu.add_command(label='%s网关' % x, command=lambda x=x: input_command(2, 0, x, None, message='VPN线路'))
        all_app_menu.add_command(label='%s网关' % x, command=lambda x=x: input_command(2, 1, x, None,  message='APP线路'))
    line_switch.add_separator()

# -----------------------------------------------------------------------------------------------------
    line_to_x_menu = tkinter.Menu(line_switch, tearoff=0, font=ch_font, bg='#d2d2d2')
    line_switch.add_cascade(label='位于线路X的VPN/APP切换到Y', menu=line_to_x_menu, font=ch_font)
    for_line_menu = {}
    for_line_menu_vpn = {}
    for_line_menu_app = {}
    for_line_menu_all = {}
    for x in Gateway_Total['VPN_Link_Common']:
        # x = x
        for_line_menu[x] = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font, bg='#b1b1b1')
        line_to_x_menu.add_cascade(label='位于线路%s' % x, menu=for_line_menu[x], font=ch_font)

        for_line_menu_vpn[x] = tkinter.Menu(for_line_menu[x], tearoff=0, font=ch_font, bg='#4b4b4b', fg='#e1e2e2')
        for_line_menu[x].add_cascade(label='的VPN', menu=for_line_menu_vpn[x], font=ch_font)

        for_line_menu_app[x] = tkinter.Menu(for_line_menu[x], tearoff=0, font=ch_font, bg='#4b4b4b', fg='#e1e2e2')
        for_line_menu[x].add_cascade(label='的APP', menu=for_line_menu_app[x], font=ch_font)

        for_line_menu_all[x] = tkinter.Menu(for_line_menu[x], tearoff=0, font=ch_font, bg='#4b4b4b', fg='#e1e2e2')
        for_line_menu[x].add_cascade(label='的所有路由', menu=for_line_menu_all[x], font=ch_font)

        for y in Gateway_Total['VPN_Link_Common']:
            # 生成切换到X.X.X.X ，如果已经处于X线路就跳过生成X的菜单，同时排除VPN_Link_Extra
            if x == y or y in Gateway_Total['VPN_Link_Extra']:
                continue
            # 将位于241的VPN路由切换到242                                                （type,sources, type, target)
            for_line_menu_vpn[x].add_command(label='切换到%s' % y, command=lambda x=x, y=y: input_command(3, x, 0, y))
            # 将位于241的app路由切换到242
            for_line_menu_app[x].add_command(label='切换到%s' % y, command=lambda x=x, y=y: input_command(3, x, 1, y))
            # 将位于241的所有路由切换到242
            for_line_menu_all[x].add_command(label='切换到%s' % y, command=lambda x=x, y=y: input_command(3, x, 2, y))
    line_switch.add_separator()

    # --------------------------------------------------------------------------------------------------
    x_to_x = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='将X路由切换到线路Y', menu=x_to_x, font=ch_font)
    separator = True
    if x_to_x_dict:
        for y in x_to_x_dict.items():
            y[1].delete('0', 'end')

        gui_text.insert('end', Dividing + '菜单已刷新！\n')
        gui_text.see('end')

    for x in Line_Status:
        for xx in x:
            temp_name = xx[-1][5:]
            x_to_x_dict[temp_name] = tkinter.Menu(x_to_x, tearoff=0, font=ch_font)
            x_to_x.add_cascade(label=temp_name, menu=x_to_x_dict[temp_name], font=ch_font)
            if xx[1] in Gateway_Total['VPN_Link_Common']:strs = '切换到'
            else:
                strs = '添加到'
            for x2 in Gateway_Total['VPN_Link_Common']:
                if xx[1] != x2:
                    x_to_x_dict[temp_name].add_command(label='%s%s' % (strs, x2), command=lambda x2=x2, xx=xx, x=x:
                    input_command(4, Line_Status.index(x), x.index(xx), x2))
                    # (type, index[1], index[index[1]], target)
            if xx[1] in Gateway_Total['VPN_Link_Common']:
                x_to_x_dict[temp_name].add_command(label='从路由表删除', command=lambda x=x, xx=xx: input_command(4, Line_Status.index(x), x.index(xx), None))
        if separator:
            x_to_x.add_separator()
            separator = False
    return False


def gui_button_panel(status):
    '生成按钮面板'
    # 首先检查是否已经生成过
    if status:
        OptionsMenu = tkinter.Frame(button_frame, width=500, height=120, bg='#FFFAFA')
        OptionsMenu.propagate(False)
        OptionsMenu.pack(side='bottom')
        # boxinfo = tkinter.messagebox.showinfo('标题1', 'this 按钮1')
        grid = {'padx': 10, 'pady': 6, 'sticky': 'ewns'}
        tkinter.Button(OptionsMenu, text='显示当前线路状态', width=17, command=show_status).grid(row=0, column=0, **grid)
        tkinter.Button(OptionsMenu, text='显示路由定义', width=17, command=show_route_def).grid(row=0, column=1, **grid)
        tkinter.Button(OptionsMenu, text='清空已缓存的命令', width=17, command=cmd_clear).grid(row=0, column=2,  **grid)

        tkinter.Button(OptionsMenu, text='刷新菜单', width=17, command=lambda: gui_line_switch_menu(True)).grid(row=1, column=0, **grid)
        tkinter.Button(OptionsMenu, text='刷新路由状态', width=17, command=lambda: flush_route_status(switch_config_t)).grid(row=1, column=1, **grid)
        tkinter.Button(OptionsMenu, text='查看已缓存的命令', width=17, command=lambda: show_cmd(False)).grid(row=1, column=2,  **grid)

        tkinter.Button(OptionsMenu, text='清空输出信息', width=17, command=clear_text).grid(row=2, column=0,  **grid)
        tkinter.Button(OptionsMenu, text='登出路由并离开', width=17, command=exit_switch).grid(row=2, column=1,  **grid)
        tkinter.Button(OptionsMenu, text='执行命令！', command=run_command, width=17, bg='#87CEEB').grid(row=2, column=2,  **grid)
        # tkinter.Button(OptionsMenu, text='读取配置文件', width=17=23, command=Read_config).grid(row=2, column=0, padx=1, pady=2)
    return False


def gui_root_frame():
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


def gui_text_frame():
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


def gui_help_menu():
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
        tkinter.Label(about_text_frame, text='V0.2 ISH专用', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 9)).pack(anchor='nw')
        tkinter.Label(about_text_frame, text='\n一个用Python和Tkinter写的Cisco路由表切换工具\n'
                                             '如遇到bug或异常请发送邮件给作者.', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='w')
        tkinter.Label(about_text_frame, text='%s' % '\n'*6, fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')
        tkinter.Label(about_text_frame, text='build:2015-11-24 15:26:50', fg='#fffafa', bg='#696969', font=('Microsoft YaHei', 8)).pack(anchor='sw')
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
        readme_text.insert('end', '\n菜单中的网关或路由条目可根据需要自行在配置文件中的对应字段中添加')
        tkinter.Button(readme, text='大概看懂了', width=12, command=lambda: readme.destroy()).pack(side='bottom', pady=5)

    help_menu.add_command(label='说明', command=readme_frame)
    help_menu.add_command(label='关于', command=about_frame)


def gui_menu_bar():
    '''生成菜单栏'''
    Menubar = tkinter.Menu(root, font=ch_font, bg='red')
    root.config(menu=Menubar)
    return Menubar

if __name__ == '__main__':
    Panel_Status = True
    Switch_Menu_Status = True
    root, button_frame, info_frame, en_font, ch_font, screensize = gui_root_frame()         # 构建主窗口
    gui_text = gui_text_frame()                                                             # 生成log框
    Menu_bar = gui_menu_bar()                                                               # 生成菜单栏
    gui_system_menu()                                                                       # 生成系统菜单
    if read_config():
        if detect_local_ip():                                                                # 检查本机IP与授权
            sh_run, switch_config_t, link = login_route(Connect_Config)                                   # 登录目标
            if link:
                Line_Status = line_detction(sh_run, Link_Static_Route, Application_Static_Route)
                Line_Set, No_Online = link_group(Line_Status)
                Switch_Menu_Status = gui_line_switch_menu()                                 # 生成链路切换菜单
                Panel_Status = gui_button_panel(Panel_Status)                               # 生成按钮面板
                gui_text.insert('end', '\nHello World！\n')
                # gui_text.insert('end', '%s' % now_time)
            else:
                gui_text.insert('end', '\n\n连接路由器失败 :(\n')
    gui_help_menu()                                                                         # 生成帮助菜单
    root.mainloop()                                                                         # 启动循环

    # nb = Notebook(info, height = 240,width=480)
    # tab = tkinter.Text(nb)
    # nb.add(tab, text='log')
    # nb.pack()
    # box2 = tkinter.Listbox(info, width=68)
    # box2.pack(side='left', fill='y')
    # box = tkinter.Message(SystemMenu,text='message' * 20,width=390,bg='red')
    # box.pack(anchor='nw')

