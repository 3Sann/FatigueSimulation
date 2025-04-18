# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import logging
import RPKtoOne
import RPOnetoK
import RPOnetoKUnBind
import RPOnetoOne
import pandas as pd
from Config import *

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    logging.basicConfig(level=log_level, format='')

    Cpicking1 = RPOnetoOne.MultiPicking()
    Cpicking2 = RPOnetoK.MultiPicking()
    Cpicking3 = RPOnetoKUnBind.MultiPicking()
    Cpicking0 = RPKtoOne.MultiRobotPicking()
    Cpicking1.run(until=SIMULATION_ELAPSE)
    Cpicking2.run(until=SIMULATION_ELAPSE)
    Cpicking3.run(until=SIMULATION_ELAPSE)
    Cpicking0.run(until=SIMULATION_ELAPSE)

    list1 = Cpicking1.output()
    list2 = Cpicking2.output()
    list3 = Cpicking3.output()
    list4 = Cpicking0.output()
    #
    print(list1)
    # print(TotalDis)
    print(list2)
    print(list3)
    print(list4)
    merge = pd.DataFrame(data=[[list1[2],list1[3],list1[9],list1[10]],
                               [list1[0],list1[1],list1[9],list1[10]],
                               [list2[0],list2[1],list2[7],list2[8]],
                               [list4[0],list4[1],list4[7],list4[8]]],
                         index=['manual','RPOnetoOne', 'RPOnetoK','RPKtoOne']).T
    print(merge)

    #outputpath = 'c:/Users/milox/Desktop/初稿/mytest.csv'
    #merge.to_csv(outputpath, sep=',', index=True, header=True)
# See PyCharm help at https://www.jetbrains.com/help/pycharm/
