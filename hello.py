print("======================")
print("我的第一个 GitHub 软件")
print("======================")

name = input("请输入你的名字：")
print(f"你好，{name}！")

while True:
    print("\n1. 计算两个数的和")
    print("2. 显示欢迎语")
    print("0. 退出")

    choice = input("请选择：")

    if choice == "1":
        a = float(input("第一个数字："))
        b = float(input("第二个数字："))
        print("结果：", a + b)
    elif choice == "2":
        print(f"欢迎你，{name}！")
    elif choice == "0":
        print("程序结束")
        break
    else:
        print("输入错误")
