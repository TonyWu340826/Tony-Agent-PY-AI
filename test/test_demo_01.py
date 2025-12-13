for x in range(1,10):
    print(f"Hello World:{x}")

for _ in range(5):
    print("World1")


for x in range(5):
    print(f"World2:{x}")

if __name__ == '__main__':
    print("This is the main program.")


toal = 0
for x in range(101):
    if x % 2 == 0:
        toal += x
        continue
print(toal)


total2 = 0
for x in range(2,101,2):
    total2 += x


print(sum(range(2,101,2)))

a = 1
match a:
    case 1:
        print('one')
    case 2:
        print('two')
    case 3:
        print('three')
    case _:
        print('other')












"""
列表
"""
items = [1,2,3,4,5,1,1,]
items.remove(1)
print(items)




"""
双色球随机选号程序
"""
import random

red_balls = [i for i in range(1, 34)]
blue_balls = [i for i in range(1, 17)]
# 从红色球列表中随机抽出6个红色球（无放回抽样）
selected_balls = random.sample(red_balls, 6)
# 对选中的红色球排序
selected_balls.sort()
# 输出选中的红色球
for ball in selected_balls:
    print(f'\033[031m{ball:0>2d}\033[0m', end=' ')
# 从蓝色球列表中随机抽出1个蓝色球
blue_ball = random.choice(blue_balls)
# 输出选中的蓝色球
print(f'\033[034m{blue_ball:0>2d}\033[0m')

















#
# """
# 双色球随机选号程序
#
# Author: 骆昊
# Version: 1.3
# """
# import random
#
# from rich.console import Console
# from rich.table import Table
#
# # 创建控制台
# console = Console()
#
# n = int(input('生成几注号码: '))
# red_balls = [i for i in range(1, 34)]
# blue_balls = [i for i in range(1, 17)]
#
# # 创建表格并添加表头
# table = Table(show_header=True)
# for col_name in ('序号 ', '红球', '蓝球'):
#     table.add_column(col_name, justify='center')
#
# for i in range(n):
#     selected_balls = random.sample(red_balls, 6)
#     selected_balls.sort()
#     blue_ball = random.choice(blue_balls)
#     # 向表格中添加行（序号，红色球，蓝色球）
#     table.add_row(
#         str(i + 1),
#         f'[red]{" ".join([f"{ball:0>2d}" for ball in selected_balls])}[/red]',
#         f'[blue]{blue_ball:0>2d}[/blue]'
#     )
#
# # 通过控制台输出表格
# console.print(table)
#
#



'''
元组
'''

# 这不是元组
v1 = (1)
print(type(v1))


v2 = [1,2]
print(type(v2))

