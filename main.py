__author__ = 'Sonny'
import ciscolib
import socket
import subprocess
import os

Gateway = '10.8.10.250'
VPN_Link = ('10.8.10.241', '10.8.10.242', '10.8.10.238', '10.0.0.6')
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

def Login_Route(gwip):                            #检测网关通路 连接到目标， 成功则返回show run
    link = True
    ping = subprocess.call("ping -n 3 -w 1 %s" % gwip, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ping == 1:
        print('无法连接到网关，请检查你的本地网络或断开本机已连接的VPN再试，仍然失败请联系开发者')
        link = False
    else:
        switch = ciscolib.Device(gwip, "ishsz")
        try:
            switch.connect()
            if switch.connected is True:
                print('成功连接到网关！')
            else:
                print('网关连接失败！')
                link = False
        except ciscolib.errors.AuthenticationError:
            print('连接认证失败！请与管理员联系')
            link = False
        except OSError:
            print('无法连接到网关，可能是管理员的安全策略导致的')
            link = False
        except socket.timeout:
            print("登录超时")
            link = False
        except AttributeError:
            print(r"内部错误，初始化失败! error code: 'NoneType' object has no attribute 'group'")
            link = False
        except ciscolib.errors.CiscoError:
            print('内部错误，初始化失败!' +
                  '\nciscolib.errors.CiscoError: Unable to get device hostname')
            link = False
        else:
            try:
                switch.enable("ishsz2008")
            except ciscolib.errors.CiscoError:
                print(r"I tried to enable, but didn't get a command nor a password prompt")
                link = False
            else:
                showrun = str((switch.cmd("show run")))
                switch.cmd('conf t')
                if showrun:
                    print('系统初始化完成!\n')
                    return showrun, switch
                else:
                    print('连接网关失败，原因未知！请与管理员联系')
                    link = False
    if link is False:
        print('\n软件即将退出!')
        exit()
        os.system('pause')

def Detect_Localip():
    link = True
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        print('本机IP获取失败，可能是系统IP协议栈错误')
        link = False
    else:
        if '192.168.5' in ip or '10.8.' in ip:
            return ip
        else:
            print('您的主机没有被授权使用本软件！\n即将退出！\n如已连接VPN请先断开.')
            link = False
    if link is False:
        os.system('pause')
        exit()

def hello():
    print('正在初始化*********************************************************************')
    print('获取本机地址...')
    print('尝试连接到网关...')

def menu(cycle):
    subprocess.call('cls', shell=True)
    print('*******************************************************************************')             #输出菜单并定义功能值
    print('----------------------------------功能选择菜单---------------------------------')
    print('-------------------------------------------------------------------------------')
    print('---------------------------------①查看当前链路状态----------------------------')
    print('---------------------------------②开始切换VPN/App线路...----------------------')
    print('---------------------------------③查看当前定义--------------------------------')
    print('---------------------------------④使用说明------------------------------------')
    print('---------------------------------⑤退出----------------------------------------')
    print('-------------------------------------------------------------------------------')
    print('*******************************************************************************')
    if cycle >= 1: input('回车以继续...')
    while True:
        num = input('键入数字以选择功能:')
        if num in '12345' and len(num) == 1:
            pass
            break
        else:
            print('没有这个选项!\n')

def Line_Detction(*args):
    #检测当前所在线路
    Line_result = []
    for group in args:
        for line in group:
            if line[0] in sh_run:
                a = sh_run.index(line[0]) + len(line[0]) + 1
                b = a + sh_run[a:].index(' ' or '\n')
                c = sh_run[a:b]
                Line_result.append([line[-1], c, line[0]])
            else:
                Line_result.append([line[-1], None, line[0]])
    return Line_result


def read():
    print("本工具用于给指定用户切换maps网络线路使用，"
          "请勿滥用作为其他用途\n如遇到bug请截图并发送到it_yangsy@ish.com.cn. 谢谢！\nversion: beta 0.2")

def switch_line(line):
    errnum = 0
    b = 0
    if line == 0:
        while True:
            line_select = input("\n本机目前处于非专用线路，" +
                            "目前有两条专用线路(1 or 2)\n请一条选择要加入的网络线路(输入1或者2)：")
            if line_select == '1':
                print("\n你选择的是线路%s" % line_select)
                print('\n正在处理中.............................\n.' +
                  '.......................................\n' * 4)
                switch.cmd('ip access-list extended source-acl-10.242')
                switch.cmd(('permit ip host %s any') % ip)
                print('现已成功加入专用线路 %s' % line_select)
                break
            elif line_select == '2':
                print("\n你选择的是线路%s" % line_select)
                print('\n正在处理中.............................\n.' +
                  '.......................................\n' * 4)
                switch.cmd('ip access-list extended source-acl-10.239')
                switch.cmd(('permit ip host %s any') % ip)
                print('\n现已成功加入专用线路 %s' % line_select)
                break
            else:
                errnum += 1
                if errnum < 3:
                    print("\n输入错误 没有这个选项，从新输入!")
                elif errnum < 4:
                    print("\n你再故意输错我就要爆炸了(〃＞皿＜)")
                else:
                    print('(╯°口°)╯(┴—┴')
                    os._exit(0)
    else:
        while True:
            a = input("在两条专线间切换输入1，要切换到普通上网线路输入2 ：")
            if a == '1' or a == '2':
                if a == '2':
                    b = 1
                break
            else:
                print('没有这个选项，请重新输入')
                a = input("在两条专线间切换输入1，要切换到普通上网线路输入2")
        print('\n正在处理中.............................\n.' +
             '.......................................\n' * 4)
        if line == 1:
            switch.cmd('ip access-list extended source-acl-10.242')
            switch.cmd(('no permit ip host %s any') % ip)
            switch.cmd('exit')
            if b == 1:
                return 1
            switch.cmd('ip access-list extended source-acl-10.239')
            switch.cmd(('permit ip host %s any') % ip)
            print("\n本机网络链路已从线路 1 切换到线路 2\n")
        elif line == 11:
            switch.cmd('ip access-list extended source-acl-10.242')
            switch.cmd(('no permit ip host %s any') % ip)
            switch.cmd('exit')
            if b == 1:
                return 1
            switch.cmd('ip access-list extended source-acl-10.239')
            switch.cmd(('permit ip host %s any') % ip)
            print("\n本机网络链路已从线路 1 切换到线路 2\n")
        if line == 2:
            switch.cmd('ip access-list extended source-acl-10.239')
            switch.cmd(('no permit ip host %s any') % ip)
            switch.cmd('exit')
            if b == 1:
                return 1
            switch.cmd('ip access-list extended source-acl-10.242')
            switch.cmd(('permit ip host %s any') % ip)
            print('本机网络链路已从线路 2 切换到线路 1\n')
        elif line == 22:
            switch.cmd('ip access-list extended source-acl-10.239')
            switch.cmd(('no permit ip host %s any') % ip)
            switch.cmd('exit')
            if b == 1:
                return 1
            switch.cmd('ip access-list extended source-acl-10.242')
            switch.cmd(('permit ip host %s any') % ip)
            print('本机网络链路已从线路 2 切换到线路 1\n')

def exitsw():
    switch_config_t.cmd('end')
    switch_config_t.cmd('exit')

if __name__ == '__main__':
    cycle = 0
    hello()
    Host_ip = Detect_Localip()                                                  #检测IP并返回IP值
    sh_run, switch_config_t = Login_Route(Gateway)                              #登录路由并返回showrun文本以及switch函数
    line = Line_Detction(Link_Static_Route, Application_Static_Route)           #检测线路并返回检测结果
    for x in line:
        print("%-35s链接接口为%15s" % (x[0], x[1]))
        print('-' * 60)

