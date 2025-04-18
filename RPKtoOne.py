import math

import simpy
import numpy as np
import logging
import random
import simpy
from typing import List, Tuple

from pandocfilters import Math

from MachineSetting2 import MachineList
from PickerSetting import PickerList
from Config import *

"""
初始化：共计k个区域,na/k也为整数，划分np个机器人均分到每个区域，每个区域np/k个机器人
对订单进行拆分，生成k个区域的订单。

"""


def get_distance(spot1, spot2):
    now_aisle = spot1[0]
    now_location = spot1[1]
    next_aisle = spot2[0]
    next_location = spot2[1]
    if (next_aisle == now_aisle):
        return abs(now_location - next_location) * WIDTH_OF_SHELVES
    else:
        if (NUM_OF_LOCATIONS > now_location + next_location):
            return abs(now_aisle - next_aisle) * WIDTH_OF_AISLE + (now_location + next_location) * WIDTH_OF_SHELVES
        else:
            return abs(now_aisle - next_aisle) * WIDTH_OF_AISLE + (
                    2 * NUM_OF_LOCATIONS - (now_location + next_location)) * WIDTH_OF_SHELVES

class MultiRobotPicking(simpy.Environment):
    def __init__(self):
        super().__init__()
        self.robots = MachineList(self, num_of_robots = NUM_OF_ROBOTS)
        self.pickers = PickerList(self, num_of_pickers = NUM_OF_PICKERS)
        self.order_idx = 1
        self.served = 0
        self.process(self.orderArrive())
        self.robot_queue_record = [0, 0] # record[0]: throughput times, record[1]: sum of all queues
        self.coTime: List[float] = []
        self.wpTime: List[float] = []
        self.waiting_time: List[float] = []  # 1/(mu-lambda)
        self.serve_time: List[float] = []
        self.total_time: List[float] = []
        self.walking_distance: List[float] = []
        self.waiting_picker: List[float] = []
        self.tempt:List[float] = []

    def travel_distance(self,this_aisle,this_location,next_aisle,next_location)->float:

        #如果同巷道，直接相减
        if (next_aisle == this_aisle):
            return abs(this_location - next_location) * WIDTH_OF_SHELVES
        else:
            #两侧距离相等
            if (NUM_OF_LOCATIONS > this_location+next_location):
                return abs(this_aisle - next_aisle) * WIDTH_OF_AISLE  + (this_location + next_location)*WIDTH_OF_SHELVES
            else:
                #很近的一侧距离
                return abs(this_aisle - next_aisle) * WIDTH_OF_AISLE + (
                        2 * NUM_OF_LOCATIONS-(this_location + next_location)) * WIDTH_OF_SHELVES


    def orderArrive(self):
        while True:
            time_interval = random.expovariate(ARRIVAL_RATE)
            yield self.timeout(time_interval)
            #logging.log(10, f"{self.now:.2f}, Batch-{self.order_idx} arrived")
            self.process(self.serve(self.order_idx))
            self.order_idx += 1

    #机器人返回depot
    def robotback(self,robotindex,robot_BacktoDepot):
            target_machine = yield self.robots.get_robotbyindex(robotindex)
            yield self.timeout(robot_BacktoDepot)
            yield self.timeout(get_distance([target_machine.aisle,0],[1/2*NUM_OF_AISLES, 0])/v_robot)
            #将返回depot的robot位置设定为0
            target_machine.location = 0
            yield self.robots.put(target_machine)

    def serve(self, client_id):
        arrive_time = self.now
        random.seed(client_id)
        orderlist: list = [0] * NUM_OF_ORDERS
        #二维数组,每一个数组代表一个area内的订单信息
        arealist = [[] for _ in range(NUM_OF_AREAS)]
        #每个区域内有多少个巷道
        aisleLimit = NUM_OF_AISLES/NUM_OF_AREAS
        for i in range(NUM_OF_ORDERS):
            orderlist[i] = [random.randint(1, NUM_OF_AISLES), random.randint(1, NUM_OF_LOCATIONS)]
        orderlist.sort(key=lambda x: (x[0], x[1]))
        for i in range(NUM_OF_ORDERS):
            originalaisle = orderlist[i][0]
            originallocation = orderlist[i][1]
            if (originalaisle % 2 == 0):
                orderlist[i] = [originalaisle, NUM_OF_LOCATIONS + 1 - originallocation]
            areamark = math.floor((originalaisle-1)/aisleLimit)
            arealist[areamark].append(orderlist[i])

        #订单的第一个货物和最后一个货物
        spot = [orderlist[0], orderlist[NUM_OF_ORDERS - 1]]

        picker, start_spot, end_spot = self.pickers.get_picker(spot=spot)
        target_picker = yield picker
        distance1 = target_picker.picker_travel_distance(start_spot)
        distance2 = target_picker.picker_travel_distance(end_spot)
        if (distance2<distance1):
            k = start_spot
            start_spot = end_spot
        #true的话说明已经调换过顺序，从最后一个订单开始拣选，那么area也要调换顺序，area里面的订单也要reverse
        if start_spot != orderlist[0]:
            for i in range(NUM_OF_AREAS): arealist[i].reverse()
            arealist.reverse()

        getPickerTime = self.now
        waiting_time = getPickerTime - arrive_time
        waiting_picker = getPickerTime - arrive_time
        serve_time = 0#服务时间
        walking_distance = 0#行走距离
        cotime=0#合作时间
        wptime=0#
        tempt=1
        sum=0

        #遍历本订单的i个area
        for i in range(NUM_OF_AREAS):
            if len(arealist[i])==0:
                continue
            else:
                #找到第i个area中的第一个货物和最后一个货物
                [start_spot, end_spot] = [arealist[i][0],arealist[i][len(arealist[i])-1]]
                target_machine = yield self.robots.get_robot(area=math.floor((start_spot[0]-1)/aisleLimit)+1, spot=start_spot)
                #记录绑定机器的时间
                getMachineTime = self.now
                #等待时间
                waiting_time += getMachineTime - getPickerTime
                #target机器人到达start spot的时间
                robot_TravelTime_1stspot = target_machine.robot_travel_distance(start_spot) / v_robot
                # 如果拣选员和start spot不是一个巷道
                if(target_picker.aisle != start_spot[0]):
                    # 相当于默认往上走
                    picker_Traveldis_1stspot = abs(target_picker.aisle - start_spot[0]) * WIDTH_OF_AISLE + int(target_picker.location + start_spot[1]) * WIDTH_OF_SHELVES
                else:
                    # 如果在一个巷道，直接location相减即可
                    picker_Traveldis_1stspot = abs(target_picker.location - start_spot[1]) * WIDTH_OF_SHELVES
                # if robot_TravelTime_1stspot>10:
                #     print([target_picker.aisle,target_picker.location],[target_machine.aisle,target_machine.location],target_machine.area,start_spot)
                # 拣选员前往start spot的时间
                picker_TravelTime_1stspot = picker_Traveldis_1stspot / v_picker
                # 前往待拣选位置的时间=max（robot,picker）
                TravelTime_1stspot = max(robot_TravelTime_1stspot, picker_TravelTime_1stspot)

                # 疲劳恢复时间（在区域间行走）
                tempt = tempt * math.e ** (-Travel_Fatigue * picker_TravelTime_1stspot)
                tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * TravelTime_1stspot)
                if tempt>1:
                    tempt=1
                sum=sum+1-tempt
                for j in range(len(arealist[i])-1):
                    tempt = tempt * math.e ** (-Pick_Fatigue * pTperItem)
                    # 行走过程疲劳变化
                    t_walk = self.travel_distance(arealist[i][j][0], arealist[i][j][1], arealist[i][j+1][0],
                                                  arealist[i][j+1][1]) / v_picker
                    #travel+recover
                    tempt = tempt * math.e ** (-Travel_Fatigue * t_walk)
                    tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * t_walk)
                    if tempt > 1:
                        tempt = 1
                    sum = sum + 1 - tempt

                #print([target_picker.aisle,target_picker.location],[target_machine.aisle,target_machine.location,target_machine.area],start_spot)
                #绑定时间
                cotime += TravelTime_1stspot
                #一次拣选，更新人的位置与行走距离
                yield self.timeout(TravelTime_1stspot)
                Picking_dis = ((2*NUM_OF_LOCATIONS - start_spot[1] - end_spot[1])*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS +
                            (aisleLimit - 2) * ((NUM_OF_LOCATIONS-1)*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS)+
                           (aisleLimit - 1) * WIDTH_OF_AISLE)
                PickingTime = Picking_dis / v_picker
                wptime+=PickingTime
                yield self.timeout(PickingTime+pTperItem * len(arealist[i]))
                target_picker.traveled_dis += (PickingTime+picker_TravelTime_1stspot) * v_picker
                target_picker.aisle = end_spot[0]
                target_picker.location = end_spot[1]
                target_machine.aisle = end_spot[0]
                target_machine.location = end_spot[1]
                walking_distance += picker_Traveldis_1stspot+Picking_dis
                robot_BacktoDepot = target_machine.robot_travel_distance([1/2*NUM_OF_AISLES, 0]) / v_robot
                getPickerTime = self.now
                target_machine.location = 0
                yield self.robots.put(target_machine)
                self.process(self.robotback(target_machine.index,robot_BacktoDepot))
                serve_time += TravelTime_1stspot + PickingTime + pTperItem * len(arealist[i])

        #最后一个订单回到depot
        tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * robot_BacktoDepot)
        if tempt > 1:
            tempt = 1
        sum = sum + 1 - tempt

        self.tempt.append(sum)

        #释放拣选员
        self.pickers.put(target_picker)
        #送回传送带
        yield self.timeout(robot_BacktoDepot)
        ##分拣的时间减短————最后一个区域的item数量
        lastAreaNum = len(arealist[NUM_OF_AREAS-1])
        yield self.timeout(sTperItem * lastAreaNum)
        self.waiting_time.append(waiting_time)
        self.coTime.append(cotime)
        self.wpTime.append(wptime)
        self.walking_distance.append(walking_distance)
        self.waiting_picker.append(waiting_picker)
        serve_time += robot_BacktoDepot + sTperItem * lastAreaNum
        self.serve_time.append(serve_time)
        self.total_time.append(self.now - arrive_time)
        ##logging.log(10, f"{self.now:.2f}, Batch-{client_id} has left, serve_time:{serve_time:.2f}, waiting time:{waiting_time:.2f}.")
        self.served = client_id
        self.robot_queue_record[0] += 1
        self.robot_queue_record[1] += len(self.robots.get_queue)



    def output(self):
        meanQuelength = self.robot_queue_record[1] / self.robot_queue_record[0]
        meanWalkingDis = sum(self.walking_distance) / len(self.walking_distance)
        meanWaitingTime = sum(self.waiting_time) / len(self.waiting_time)
        meanServiceTime = sum(self.serve_time) / len(self.serve_time)
        meanTotalTime = sum(self.total_time) / len(self.total_time)
        meanFatigue = sum(self.tempt) / len(self.tempt)
        logging.log(50, "RPktoOne\n"
                        f"{'-' * 30}\nTotal Simulation time: {SIMULATION_ELAPSE} s\n"
                        f"Arrive: {self.order_idx}\n"
                        f"Served: {self.served}\n"
                        f"Mean Queue Length:{self.robot_queue_record[1] / self.robot_queue_record[0]:.2f}\n"
                        f"Mean Walking Distance:{sum(self.walking_distance) / len(self.walking_distance):.2f} m\n"
                        f"Mean Waiting Time:{sum(self.waiting_time) / len(self.waiting_time):.2f} s\n"
                        f"Mean Waiting Picker:{sum(self.waiting_picker) / len(self.waiting_picker):.2f} s\n"
                        f"Mean Service Time:{sum(self.serve_time) / len(self.serve_time):.2f} s\n"
                        f"Mean Total Time:{sum(self.total_time) / len(self.total_time):.2f} s\n"
                        f"Mean co Time:{sum(self.coTime) / len(self.coTime):.2f} s\n"
                        f"Mean wptime:{sum(self.wpTime) / len(self.wpTime):.2f} s\n"
                        )
        mylist = list((meanFatigue,meanFatigue/NUM_OF_ORDERS,self.order_idx,self.served,meanQuelength,meanWalkingDis,meanWaitingTime,meanServiceTime,meanTotalTime))
        return mylist

