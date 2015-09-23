__author__ = 'Sonny'
import ciscolib
import socket
import subprocess
import os

Gateway = '10.8.10.251'

Link_Static_Route = (["ip route 10.8.100.0 255.255.252.0 10.8.10.241 name TO-SZ-Shajin",    "深圳-沙井"],
                     ["ip route 10.12.0.0 255.255.252.0 10.8.10.241 name TO-Xinxiang",      "新乡"],
                     ["ip route 10.13.1.0 255.255.255.0 10.8.10.241 name TO-Foshan-WH",     "佛山运作"],
                     ["ip route 10.13.3.0 255.255.255.0 10.8.10.241 name TO-Foshan-OFFICE", "佛山办公室"],
                     ["ip route 10.16.0.0 255.255.252.0 10.8.10.242 name TO-Shanghai",      "上海"],
                     ["ip route 10.17.0.0 255.255.252.0 10.8.10.242 name TO-Beijing",       "北京"],
                     ["ip route 10.127.0.0 255.255.252.0 10.8.10.242 name TO-HK",           "香港"],
                     ["ip route 10.69.1.0 255.255.255.0 10.8.10.242 name TO-XM-Yuanchu",    "厦门 元初"],
                     ["ip route 10.68.0.0 255.255.252.0 10.0.0.6 name TO-XM-Fibre-4M",      "厦门办公专线"],
                     ["ip route 172.18.0.0 255.255.0.0 10.0.0.6 name TO-XM-LenovoLAN"       "厦门联想专线"])

Application_Static_Route = ("ip route 103.30.232.33 255.255.255.255 10.8.10.242 name For-IPG",
                            "ip route 202.14.67.0 255.255.255.0 10.8.10.242 name For-DNS-PACnet",
                            "ip route 202.96.27.0 255.255.255.0 10.8.10.242 name For-LENOVO-INTERFACE-BACKUP",
                            "ip route 203.247.130.80 255.255.255.255 10.8.10.241 name For-LG-CHEM",
                            "ip route 216.228.121.21 255.255.255.255 10.8.10.242 name For-NVIDIA",
                            "ip route 219.134.185.204 255.255.255.255 10.8.10.242 name For-IE-Penghaiyun",
                            "ip route 219.141.216.0 255.255.255.0 10.8.10.241 name For-LENOVO-INTERFACE"
                            )

def route(gwip):                            #检测网关通路 连接到目标， 成功则返回show run
    #log = dict([('show run', showrun)])
    ping = subprocess.call("ping -n 3 -w 1 %s" % gwip, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ping == 1:
        print('无法连接到网关，请检查你的本地网络或断开本机已连接的VPN再试，仍然失败请联系开发者')
        return False, None, None
    else:
        switch = ciscolib.Device(gwip, "xxxxx")
        try:
            switch.connect()
            if switch.connected == True:
                print('成功连接到网关！')
            else:
                print('网关连接失败！')
                return False, None, None
        except ciscolib.errors.AuthenticationError:
            print('连接认证失败！请与管理员联系')
            return False, None, None
        except OSError:
            print('无法连接到网关，可能是管理员的安全策略导致的')
            return False, None, None
        except socket.timeout:
            print("登录超时")
            return False, None, None
        except AttributeError:
            print(r"内部错误，初始化失败，软件即将退出! error code: 'NoneType' object has no attribute 'group'")
            return False, None, None
        except ciscolib.errors.CiscoError:
            print('内部错误，初始化失败，软件即将退出!' +
                  '\nciscolib.errors.CiscoError: Unable to get device hostname')
            return False, None, None
        else:
            try:
                switch.enable("xxxxxx")
            except ciscolib.errors.CiscoError:
                print(r"I tried to enable, but didn't get a command nor a password prompt")
                return False, None, None
            showrun = str((switch.cmd("show run")))
            switch.cmd('conf t')
            if showrun != None:
                print('成功登录特权模式')
                return True, showrun, switch
            else:
                print('连接网关失败，原因未知！请与管理员联系')
                return False, None, None

def localip():
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        print('本机IP获取失败，可能是系统IP协议栈错误')
        return False, None
    else:
        if '192.168.5' in ip or '192.168.4' in ip or '10.8.' in ip:
            return True, ip
        else:
            print('您的主机没有被授权使用本软件！\n即将退出！\n如已连接VPN请先断开.')
            os.system('pause')
            return False, None

def hello():
    print('正在初始化*********************************************************************')
    print('获取本机地址...')
    print('尝试连接到网关...')

def menu(xh):
    subprocess.call('cls', shell=True)
    print('*******************************************************************************')             #输出菜单并定义功能值
    print('----------------------------------功能选择菜单---------------------------------')
    print('-------------------------------------------------------------------------------')
    print('---------------------------------①检测各VPN所在线路---------------------------')
    print('---------------------------------②开始切换VPN线路......-----------------------')
    print('---------------------------------③查看当前定义--------------------------------')
    print('---------------------------------③使用说明------------------------------------')
    print('---------------------------------④退出----------------------------------------')
    print('-------------------------------------------------------------------------------')
    print('*******************************************************************************')
    if xh >= 1: input('回车以继续...')
    num = input('键入数字以选择功能:')
    while True:
        if num == '1':
            return 1
        if num == '2':
            return 2
        if num == '3':
            return 3
        if num == '4':
            return 4
        else:
            print('没有这个选项，请重新输入：')
            num = input('键入数字以选择功能:')

def line_detction():                                             #检测当前所在线路
    if (("host %s") % ip) in shrun:
        a = shrun.find('ip access-list extended source-acl-10.239')       #提取239网关字段
        b = shrun.find('ip access-list extended source-acl-10.240')
        a1 = shrun.find('ip access-list extended source-acl-10.242')      #提取242网关字段
        b1 = shrun.find('!', a1)
        vigor = shrun[a:b]
        asa242 = shrun[a1:b1]
        if (('permit ip host %s any') % ip) in asa242:
            return 1
        elif (('permit ip host %s any') % ip) in asa242:
            return 11
        elif (('permit ip host %s any') % ip) in vigor:
            return 22
        elif (('permit ip host %s any') % ip) in vigor:
            return 2
        else:
            print('检测到本机处于非常规配置，请联系管理员手动处理')
            return None
    else:           #没有在配置文件找到本机相关信息
        return 0

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
    switch.cmd('end')
    switch.cmd('exit')

if __name__ == '__main__':
    xunhuan = 0
    hello()
    localipre, ip = localip()                       #检测IP并返回IP值
    if localipre == False:
        os._exit(0)
    while True:
        switch_line_re = 0
        routere, shrun, switch = route(gwip)        #登录路由并返回showrun文本以及switch函数
        if localipre and routere:
            print('系统初始化完成!')
            line = line_detction()                  #检测线路并返回检测结果
            menuer = menu(xunhuan)         #返回第一菜单值
            if menuer == 1:         #检测线路
                if line == 2 or line == 22:             #vigor 10.239出口
                    print('本机当前处于专线2')
                elif line == 1 or line == 11:             #asa 10.242出口
                    print('本机当前处于专线1')
                elif line == 0:
                    print('本机未配置为专用线路')
                print('即将返回主菜单！')
                exitsw()
            elif menuer == 2:
                switch_line_re = switch_line(line)
                exitsw()
            elif menuer == 3:
                read()
                exitsw()
            elif menuer == 4:
                os._exit(0)
            elif menuer == None:
                exitsw()
                os._exit(0)
            if switch_line_re == 1:
                print("已切换到普通上网线路！")
            os.system('pause')
            xunhuan += 1
        else:
            print('初始化失败，软件即将退出')
            os.system('pause')
            os._exit(0)