"""
Maya Bridge - Maya 端启动脚本

在 Maya 的 Script Editor 中运行此脚本，或将其加入 userSetup.py。
它会打开一个 commandPort，让 Node.js 中间层可以通过 TCP 发送 Python 命令。

默认端口: 12345（与 server.js 中的 MAYA_PORT 对应）
"""
import maya.cmds as cmds

PORT = 12345

def open_command_port(port=PORT):
    """打开 Maya commandPort，接收 Python 命令"""
    port_name = ':{}'.format(port)

    # 如果端口已打开，先关闭再重开
    if cmds.commandPort(port_name, query=True):
        cmds.commandPort(name=port_name, close=True)
        print('[Maya Bridge] 已关闭旧端口: {}'.format(port))

    cmds.commandPort(
        name=port_name,
        sourceType='python',
        echoOutput=False,
        noreturn=False,
        bufferSize=4096,
    )
    print('[Maya Bridge] commandPort 已打开: localhost:{}'.format(port))
    print('[Maya Bridge] 现在可以从网页控制面板发送命令了')

def close_command_port(port=PORT):
    """关闭 Maya commandPort"""
    port_name = ':{}'.format(port)
    if cmds.commandPort(port_name, query=True):
        cmds.commandPort(name=port_name, close=True)
        print('[Maya Bridge] commandPort 已关闭: {}'.format(port))
    else:
        print('[Maya Bridge] 端口未打开: {}'.format(port))

# 自动执行
open_command_port()
