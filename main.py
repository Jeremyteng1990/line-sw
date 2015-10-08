# -*- coding: utf-8 -*-
__author__ = 'Sonny'
import ciscolib
import socket
import subprocess
import os
import tkinter
import tkinter.messagebox
import tkinter.font
import tkinter.ttk
from tkinter.ttk import Notebook
import time
import sys
import logging
from multiprocessing import Process
from multiprocessing.queues import Queue
from threading import Thread
import tkinter.filedialog




Cmd = [[], []]
Dividing = '\n\n' + '--*--' * 13 + '\n\n'
Gateway = '10.8.10.250'
VPN_Link = ['10.8.10.241', '10.8.10.242', '10.0.0.6']
Link_Static_Route = (["ip route 10.8.100.0 255.255.252.0", "name TO-SZ-Shajin",],
                     ["ip route 10.12.0.0 255.255.252.0", "name TO-Xinxiang"],
                     ["ip route 10.13.1.0 255.255.255.0", "name TO-Foshan-WH"],
                     ["ip route 10.13.3.0 255.255.255.0", "name TO-Foshan-OFFICE"],
                     ["ip route 10.16.0.0 255.255.252.0", "name TO-Shanghai"],
                     ["ip route 10.17.0.0 255.255.252.0", "name TO-Beijing"],
                     ["ip route 10.127.0.0 255.255.252.0", "name TO-HK"],
                     ["ip route 10.69.1.0 255.255.255.0", "name TO-XM-Yuanchu"],
                     ["ip route 10.68.0.0 255.255.252.0", "name TO-XM-Fibre-4M"],
                     ["ip route 172.18.0.0 255.255.0.0", "name TO-XM-LenovoLAN"])

Application_Static_Route = (["ip route 103.30.232.33 255.255.255.255",  "name For-IPG"],
                            ["ip route 202.14.67.0 255.255.255.0",      "name For-DNS-PACnet"],
                            ["ip route 202.96.27.0 255.255.255.0",      "name For-LENOVO-INTERFACE-BACKUP"],
                            ["ip route 203.247.130.80 255.255.255.255", "name For-LG-CHEM"],
                            ["ip route 216.228.121.21 255.255.255.255", "name For-NVIDIA"],
                            ["ip route 219.134.185.204 255.255.255.255","name For-IE-Penghaiyun"],
                            ["ip route 219.141.216.0 255.255.255.0",    "name For-LENOVO-INTERFACE"]
                            )


def Login_Route(gwip):                            # 检测网关通路 连接到目标， 成功则返回show run
    link = True
    ping = subprocess.call("ping -n 3 -w 1 %s" % gwip, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ping == 1:
        gui_text.insert('end', Dividing + '无法连接到网关，请检查你的本地网络连接是否正常!\n')
        link = False
    else:
        switch = ciscolib.Device(gwip, "ishsz")
        try:
            switch.connect()
        except Exception as err:
            gui_text.insert('end', Dividing + str(err))
            link = False
        else:
            try:
                switch.enable("ishsz2008")
            except Exception as err:
                gui_text.insert('end', Dividing + str(err))
                link = False
            else:
                showrun = str((switch.cmd("show run")))
                switch.cmd('conf t')
                print('系统初始化完成!\n')
                return showrun, switch, link

    return None, None, link


def Detect_Localip():
    link = True
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception as err:
        tkinter.messagebox.showerror('错误', str(err))
        # output.insert('0.0', err)
        link = False
    else:
        if '192.168.5' in ip or '10.8.' in ip:
            return ip
        else:
            tkinter.messagebox.showerror('错误', '您的主机没有被授权使用本软件,无法继续操作！\n如在内网已连接VPN请先断开再试！\n')
            link = False
    if not link:
        exit()


def Line_Detction(sh_run, *args):
    # 检测当前所在线路
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


def read():
    print("本工具用于给指定用户切换maps网络线路使用，"
          "请勿滥用作为其他用途\n如遇到bug请截图并发送到it_yangsy@ish.com.cn. 谢谢！\nversion: beta 0.2")


def Link_Group(line_status):
    # readme = [[vpn], [app]]
    line_241 = [[], []]
    line_242 = [[], []]
    line_XM = [[], []]
    for group in line_status:
        for line in group:
            if line[1] == VPN_Link[0]:
                line_241[line_status.index(group)].append([line[0], line[-1]])
            elif line[1] == VPN_Link[1]:
                line_242[line_status.index(group)].append([line[0], line[-1]])
            elif line[1] == VPN_Link[2]:
                line_XM[line_status.index(group)].append([line[0], line[-1]])
            else:
                print('%s 当前不存在！' % line[0])
    return line_241, line_242, line_XM


def Link_Switching(options, *args):
    global Cmd
    a, b, c, d = options[0], options[1], options[2], options[3]
    if d:
        xm = False
    else:
        xm = True

    if a == 1:                                            # 全体切换到241/242
        target_line = b - 1
        for gw in args:
            if args.index(gw) == target_line:
                continue
            for group in gw:
                for iproute in group:
                    Cmd[0].append('no ' + iproute[0] + ' ' + VPN_Link[args.index(gw)])
                    Cmd[1].append(iproute[0] + ' ' + VPN_Link[target_line] + ' ' + iproute[-1])
            if xm:
                break
    elif a == 2:                                          # vpn/app 切换到 241/242
        sources_type = b - 1
        target_line = c - 1
        for gw in args:
            if args.index(gw) == target_line:
                continue
            for group in gw[sources_type]:
                Cmd[0].append('no ' + group[0] + ' ' + VPN_Link[args.index(gw)])
                Cmd[1].append(group[0] + ' ' + VPN_Link[target_line] + ' ' + group[-1])
            if xm:
                break
    elif a == 3:                                        # 位于X的Y切换到Z
        # vpn_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 1, 2))       # 将位于241的VPN路由切换到242
        # app_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 2, 2))       # 将位于241的app路由切换到242
        # all_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 3, 2))       # 将位于241的所有路由切换到242
        sources_line = b - 1
        if c is 1 or c is 2:
            aa = c - 1
        else:
            aa = 0
        target_line = d - 1
        for gw in args[sources_line][aa:c]:
            for group in gw:
                Cmd[0].append('no ' + group[0] + ' ' + VPN_Link[sources_line])
                Cmd[1].append(group[0] + ' ' + VPN_Link[target_line] + ' ' + group[-1])

    elif a == 4:                                        # 将线路X 切换到出口Y
        global Line_Status
        if Line_Status[b][c][1]:
            Cmd[0].append('no ' + Line_Status[b][c][0] + ' ' + Line_Status[b][c][1])
        Cmd[1].append(Line_Status[b][c][0] + ' ' + VPN_Link[d] + ' ' + Line_Status[b][c][-1])

    # print('\n你的操作将执行以下命令:')
    # return cmd


def Command():             # 执行命令
    try:
        for x in Cmd:
            for xx in x:
                switch_config_t.cmd(xx)
    except Exception as err:
        gui_text.insert('end', Dividing + '执行命令出现错误:\n' + str(err))
    else:
        gui_text.insert('end', Dividing + '命令已执行完毕！\n')
        Flush_Route_Status()    # 刷新状态
    gui_text.see('end')


def Flush_Route_Status():       # 刷新路由状态
    global Line_Status, sh_run
    try:
        switch_config_t.cmd('end')
        sh_run = str(switch_config_t.cmd('show run'))
        Line_Status = Line_Detction(sh_run, Link_Static_Route, Application_Static_Route)
    except Exception as err:
        gui_text.insert('end', Dividing + '刷新路由状态失败:\n' + str(err))
    else:
        gui_text.insert('end', Dividing + '路由状态已刷新！')
    gui_text.see('end')


def exitsw(tab, switch_config_t):
    try:
        switch_config_t.cmd('end')
        switch_config_t.cmd('exit')
        exit()
    except Exception as err:
        tab.insert('end', Dividing + '退出出现错误:\n' + str(err))
        gui_text.see('end')


def Show_Cmd():         # 显示当前缓存的命令
    if Cmd != [[], []]:
        gui_text.insert('end', Dividing + '当前缓存的命令如下:\n')
        for x in Cmd:
            for xx in x:
                gui_text.insert('end', xx+'\n')
        gui_text.see('end')
    else:
        gui_text.insert('end',  Dividing + '当前没有缓存命令!')
        gui_text.see('end')


def Cmd_Clear():        # 清除缓存的命令
    global Cmd
    Cmd = [[], []]
    gui_text.insert('end', Dividing + '已清空！')
    gui_text.see('end')


def all_object_menu_box(message, *args):                          # 全体对象切换到X --> 切换到241/242网关
        re = tkinter.messagebox.askyesnocancel(title='额外选项', message='是否包含厦门专线10.0.0.6上的%s ?' % message)
        if re is None:
            pass
        else:
            Link_Switching([args[0], args[1], args[2], re], Line_241, Line_242, Line_XM)
            gui_text.insert('end', Dividing + '以下命令已缓存，可以开始执行命令！\n')
            for x in Cmd:
                for xx in x:
                    gui_text.insert('end', xx+'\n')
            gui_text.see('end')          # 滚动条滚动到末尾


def input_command(*args):
        Link_Switching([args[0], args[1], args[2], args[3]], Line_241, Line_242, Line_XM)
        gui_text.insert('end', Dividing + '以下命令已缓存，可以开始执行命令！\n')
        for x in Cmd:
            for xx in x:
                gui_text.insert('end', xx+'\n')
        gui_text.see('end')          # 滚动条滚动到末尾


def Show_Status():              # 显示当前线路状态
        gui_text.insert('end', Dividing)
        for x in Line_Status:
            for xx in x:
                gui_text.insert('end', "%-35s链路接口为%15s" % (xx[-1][5:], xx[1]) + '\n' + '-' * 60 + '\n')
        # tab.focus_force() 光标移动至末尾
        gui_text.see('end')          # 滚动条滚动到末尾


def Show_Route_Def():           # 显示路由定义
    route_len = 0
    name_len = 0
    gui_text.insert('end', Dividing)
    for x in [Link_Static_Route, Application_Static_Route]:
        for xx in x:
            if route_len < len(xx[0]):route_len = len(xx[0])
            if name_len < len(xx[1]):name_len = len(xx[1])
    for x in [Link_Static_Route, Application_Static_Route]:
        for xx in x:
            gui_text.insert('end', '%-*s %-*s' % (route_len, xx[0], name_len - 5, xx[1][5:]) + '\n' + '-' * 67 + '\n')
    gui_text.see('end')


def Clear_Text():                # 清空output
        gui_text.delete('0.0', 'end')

if __name__ == '__main__':
    # GUI框架
    root = tkinter.Tk()
    root.geometry('500x600')
    root.title('Hello World')
    # top_info_frame = tkinter.Frame(root, width=500, height=30, bg='green')
    # top_info_frame.propagate(False)
    # # top_info_frame.pack()
    button_frame = tkinter.Frame(root, width=500, height=200, bg='#E0FFFF')
    button_frame.propagate(False)
    button_frame.pack()
    en_font = tkinter.font.Font(family='Arial', size=10, weight='normal')
    ch_font = tkinter.font.Font(family='Microsoft YaHei', size=10, weight='normal')
    tkinter.Label(root, text='Output Info:', font=en_font, bg='white').pack(fill='x', anchor='w')
    info = tkinter.Frame(root, width=500, height=350, bg='#808080')                           # 输出文本之框架
    info.propagate(False)
    info.pack()
# --------------------------------------------------------------------------------------------
    gui_text = tkinter.Text(info, width=68, height=26)
    # gui_text.bind("<KeyPress>", lambda e: "break")
    gui_text.pack(side='left')      # , fill='y'
    gui_text.insert('end', 'Hello World!\n')

    scrollbar = tkinter.ttk.Scrollbar(info, orient='vertical', command=gui_text.yview)
    scrollbar.pack(side='right', fill='y')
    gui_text['yscrollcommand'] = scrollbar.set

    Detect_Localip()
    sh_run, switch_config_t, link = Login_Route(Gateway)
    if link is False:
        gui_text.insert('end', '连接路由器失败\n')
    else:
        Line_Status = Line_Detction(sh_run, Link_Static_Route, Application_Static_Route)
        Line_241, Line_242, Line_XM = Link_Group(Line_Status)
# ---------------------------------------------------------------------------------------------

    OptionsMenu = tkinter.Frame(button_frame, width=350, height=200)
    OptionsMenu.propagate(False)
    OptionsMenu.pack(side='left')
    #  boxinfo = tkinter.messagebox.showinfo('标题1', 'this 按钮1')
    tkinter.Button(OptionsMenu, text='显示当前线路状态', width=23, command=Show_Status).grid(row=0, column=0, sticky='w', padx=1, pady=2)
    tkinter.Button(OptionsMenu, text='显示路由定义', width=23, command=Show_Route_Def).grid(row=0, column=1, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='所有VPN线路切换到241出口').grid(row=1, column=0, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='所有VPN线路切换到242出口').grid(row=2, column=0, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='所有APP线路切换到241出口').grid(row=3, column=0, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='所有APP线路切换到242出口').grid(row=4, column=0, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='将241线路VPN切换到242出口').grid(row=1, column=1, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='将241线路APP切换到242出口').grid(row=2, column=1, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='将242线路VPN切换到241出口').grid(row=3, column=1, padx=1, pady=2)
    # tkinter.Button(OptionsMenu, text='将242线路APP切换到241出口').grid(row=4, column=1, padx=1, pady=2)

    SystemMenu = tkinter.Frame(button_frame, width=150, height=200, bg='#ffffe0')
    SystemMenu.propagate(False)
    SystemMenu.pack(side='right')
    tkinter.Button(SystemMenu, text='清空输出信息', width=14, command=Clear_Text).pack(expand='yes')
    tkinter.Button(SystemMenu, text='退出', width=14, command=lambda: exitsw(gui_text, switch_config_t)).pack(expand='yes')
    tkinter.Button(SystemMenu, text='查看已缓存的命令', width=14, command=Show_Cmd).pack(expand='yes')
    tkinter.Button(SystemMenu, text='清空已缓存的命令', width=14, command=Cmd_Clear).pack(expand='yes')
    tkinter.Button(SystemMenu, text='执行命令！', width=14, bg='#87CEEB').pack(expand='yes')

    Menubar = tkinter.Menu(root, font=('Arial', 15), bg='red')
    root.config(menu=Menubar)

    filemenu = tkinter.Menu(Menubar, tearoff=0, font=en_font)
    filemenu.add_command(label='Open')
    filemenu.add_checkbutton(label='save')
    filemenu.add_separator()
    Menubar.add_cascade(label='File', menu=filemenu)

    line_switch = tkinter.Menu(Menubar, tearoff=0, font=en_font)
    Menubar.add_cascade(label='线路切换', menu=line_switch)
    # -------------------------------------------------------------------------------------------------
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
    vpn_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 1, 2))       # 将位于241的VPN路由切换到242
    app_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 2, 2))       # 将位于241的app路由切换到242
    all_line_1.add_command(label='切换到242', command=lambda: input_command(3, 1, 3, 2))       # 将位于241的所有路由切换到242

    line_242 = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font)
    line_to_x_menu.add_cascade(label='位于线路242', menu=line_242, font=ch_font)
    vpn_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    app_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    all_line_2 = tkinter.Menu(line_242, tearoff=0, font=ch_font)
    vpn_line_2.add_command(label='切换到241', command=lambda: input_command(3, 2, 1, 1))
    app_line_2.add_command(label='切换到241', command=lambda: input_command(3, 2, 2, 1))
    all_line_2.add_command(label='切换到241', command=lambda: input_command(3, 2, 3, 1))
    line_242.add_cascade(label='的VPN', menu=vpn_line_2, font=ch_font)
    line_242.add_cascade(label='的APP', menu=app_line_2, font=ch_font)
    line_242.add_cascade(label='的所有路由', menu=all_line_2, font=ch_font)

    line_xm = tkinter.Menu(line_to_x_menu, tearoff=0, font=ch_font)
    line_to_x_menu.add_cascade(label='位于线路0.6', menu=line_xm, font=ch_font)
    xm_line = tkinter.Menu(line_xm, tearoff=0, font=ch_font)
    line_xm.add_cascade(label='的VPN链路', menu=xm_line, font=ch_font)
    xm_line.add_command(label='切换到241', command=lambda: input_command(3, 3, 1, 1))
    xm_line.add_command(label='切换到242', command=lambda: input_command(3, 3, 1, 2))
    line_switch.add_separator()
    # --------------------------------------------------------------------------------------------------
    x_to_x = tkinter.Menu(line_switch, tearoff=0, font=ch_font)
    line_switch.add_cascade(label='将X路由切换到线路Y', menu=x_to_x, font=ch_font)
    # x_to_x_menu_dict = {}         存储动态变量

    for x1 in Line_Status:
        for x2 in x1:
            a = tkinter.Menu(x_to_x, tearoff=0, font=ch_font)
            x_to_x.add_cascade(label=x2[-1][5:], menu=a, font=ch_font)
            for x3 in VPN_Link:
                if x2[1] != x3:
                    # command=lambda x3=x3 , x1=x1, x2=x2: input_command   创建当前循环的快照
                    a.add_command(label='切换到%s' % x3, command=lambda x3=x3 , x1=x1, x2=x2: input_command(4, Line_Status.index(x1), x1.index(x2), VPN_Link.index(x3)))
    # --------------------------------------------------------------------------------------------------
    help_menu = tkinter.Menu(Menubar, tearoff=0, font=ch_font)
    Menubar.add_cascade(label='帮助', menu=help_menu, font=ch_font)

    #                    print(Line_Status.index(x1), x1.index(x2), VPN_Link.index(x3))
    #                 x_to_x_a[x2[-1][5:]] = Line_Status.index(x1)
    #                 x_to_x_b[x2[-1][5:]] = x1.index(x2)
    #                 x_to_x_c[x2[-1][5:]] = VPN_Link.index(x3)
    #                 x_to_x_label[x2[-1][5:]] = '切换到%s' % x3
    # for xx1 in x_to_x_menu_dict.items():
    #     xx1[1].add_command(label=x_to_x_label[xx1[0]], command=lambda: input_command(4, x_to_x_a[xx1[0]], x_to_x_b[xx1[0]], x_to_x_c[xx1[0]]))
    #

                   # x_to_x_menu_dict[x2[-1][5:]].add_command(label='切换到%s' % x3, command=lambda: input_command(4,a,b,c))


                    #                     # .add_command(label='切换到%s' % x3, command=lambda: input_command(4,1,1,1))
                    #
                    #             for x3 in VPN_Link:

            # if x2[1] == '10.8.10.241':
            #     tempdict[x2[-1][5:]].add_command(label='切换到10.8.10.242', command=lambda:input_command(4, 1, 1, 1))
            #     tempdict[x2[-1][5:]].add_command(label='切换到10.0.0.6', command=lambda:input_command(4, 1, 1, 2))
            # elif x2[1] == '10.8.10.242':
            #     tempdict[x2[-1][5:]].add_command(label='切换到241', command=lambda:input_command(4, 1, 1, 0))
            #     tempdict[x2[-1][5:]].add_command(label='切换到10.0.0.6', command=lambda:input_command(4, 1, 1, 2))
            # elif x2[1] == '10.0.0.6':
            #     tempdict[x2[-1][5:]].add_command(label='切换到241', command=lambda:input_command(4, 1, 1, 0))
            #     tempdict[x2[-1][5:]].add_command(label='切换到242', command=lambda:input_command(4, 1, 1, 1))
            # else:
            #     tempdict[x2[-1][5:]].add_command(label='切换到241', command=lambda:input_command(4, 1, 1, 0))
            #     tempdict[x2[-1][5:]].add_command(label='切换到242', command=lambda:input_command(4, 1, 1, 1))
            #     tempdict[x2[-1][5:]].add_command(label='切换到10.0.0.6', command=lambda:input_command(4, 1, 1, 2))


    # nb = Notebook(info, height = 240,width=480)
    # tab = tkinter.Text(nb)
    # nb.add(tab, text='log')
    # nb.pack()

    root.mainloop()

#    box2 = tkinter.Listbox(info, width=68)
#    box2.pack(side='left', fill='y')


# box = tkinter.Message(SystemMenu,text='message' * 20,width=390,bg='red')
# box.pack(anchor='nw')


#if __name__ == '__main__':

    #cycle = 0
    # hello()
    # Host_ip = Detect_Localip()                                                          # 检测IP并返回IP值
    # sh_run, switch_config_t = Login_Route(Gateway)                                      # 登录路由并返回showrun文本以及switch函数
    # Line_Status = Line_Detction(Link_Static_Route, Application_Static_Route)            # 检测线路并返回检测结果
    # Gui()
    # Line_241, Line_242, Line_XM = Link_Group(Line_Status)
    # mune_result = ['4','0','2','1']
    # cmd = Link_Switching(mune_result, Line_241, Line_242, Line_XM)
    # for y in cmd:
    #     for yy in y:
    #         print(yy)

