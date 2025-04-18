import math

import simpy
import numpy as np
import logging
import random
import simpy
from typing import List, Tuple

from pandocfilters import Math

from MachineSetting import MachineList
from PickerSetting import PickerList
from Config import *
from RPOnetoKUnBind import get_distance

"""
初始化：共计k个区域,na/k也为整数，划分np个拣选员均分到每个区域，每个区域np/k个人
对订单进行拆分，生成k个区域的订单。
对订单列表进行循环，每次呼叫该区域的拣选员。

"""
class MultiPicking(simpy.Environment):
    def __init__(self):
        super().__init__()
        self.robots = MachineList(self, num_of_robots = NUM_OF_ROBOTS)
        self.pickers = PickerList(self, num_of_pickers = NUM_OF_PICKERS)
        self.order_idx = 1
        self.served = 0
        self.process(self.orderArrive())
        self.robot_queue_record = [0, 0] # record[0]: throughput times, record[1]: sum of all queues
        self.waiting_time: List[float] = []  # 1/(mu-lambda)
        self.serve_time: List[float] = []
        self.total_time: List[float] = []
        self.walking_distance: List[float] = []
        self.tempt:List[float] = []
        self.tempt1:List[float] = []

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
            #批次到达间隔
            time_interval = random.expovariate(ARRIVAL_RATE)
            yield self.timeout(time_interval)
            #logging.log(10, f"{self.now:.2f}, Batch-{self.order_idx} arrived")
            self.process(self.serve(self.order_idx))
            self.order_idx += 1

    def serve(self, client_id):
        arrive_time = self.now
        random.seed(client_id)
        orderlist: list = [0] * NUM_OF_ORDERS
        #给300个order随机赋位置信息，批次订单300个
        for i in range(NUM_OF_ORDERS):
            orderlist[i] = [random.randint(1, NUM_OF_AISLES), random.randint(1, NUM_OF_LOCATIONS)]
        orderlist.sort(key=lambda x: (x[0], x[1]))

        #如果巷道数是偶数的话，S型拣选路径时，将位置信息变更
        for i in range(NUM_OF_ORDERS):
            originalaisle = orderlist[i][0]
            originallocation = orderlist[i][1]
            if (originalaisle % 2 == 0):
                orderlist[i] = [originalaisle, NUM_OF_LOCATIONS + 1 - originallocation]

        spot = [orderlist[0], orderlist[NUM_OF_ORDERS - 1]]
        picker, start_spot, end_spot = self.pickers.get_picker(spot)
        target_machine = yield self.robots.get_robot(start_spot)
        target_picker = yield picker
        distance1 = target_picker.picker_travel_distance(start_spot)
        distance2 = target_picker.picker_travel_distance(end_spot)
        #交换start point和end point
        if (distance2 < distance1):
            k = start_spot
            start_spot = end_spot
            end_spot = k
        #等待时间
        waiting_time = self.now - arrive_time
        self.waiting_time.append(waiting_time)
        #robot travel去start spot的时间
        robot_TravelTime_1stspot = target_machine.robot_travel_distance(start_spot) / v_robot
        #如果拣选员和start spot不是一个巷道
        if (target_picker.aisle != start_spot[0]):
            #相当于默认往上走
            picker_Traveldis_1stspot = abs(target_picker.aisle - start_spot[0]) * WIDTH_OF_AISLE + (
                        target_picker.location + start_spot[1]) * WIDTH_OF_SHELVES
        else:
            #如果在一个巷道，直接location相减即可
            picker_Traveldis_1stspot = abs(target_picker.location - start_spot[1]) * WIDTH_OF_SHELVES
        #拣选员前往start spot的时间
        picker_TravelTime_1stspot = picker_Traveldis_1stspot / v_picker

        if (picker_TravelTime_1stspot) * v_picker > 40:
            print(picker_TravelTime_1stspot * v_picker, target_picker.aisle,target_picker.location,start_spot)
        #前往待拣选位置的时间=max（robot,picker）
        TravelTime_1stspot = max(robot_TravelTime_1stspot, picker_TravelTime_1stspot)
        yield self.timeout(TravelTime_1stspot)
        # 由于是一机一人绑定模式，加上遍历的时间，计算最后一个点与第一个点之间的路程。
        PickingTime = ((2*NUM_OF_LOCATIONS - start_spot[1] - end_spot[1])*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS +
                        (NUM_OF_AISLES - 2) * ((NUM_OF_LOCATIONS-1)*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS)+
                       (NUM_OF_AISLES - 1) * WIDTH_OF_AISLE) / v_picker

        # target_picker.traveled_dis += PickingTime * v_picker
        target_picker.aisle = end_spot[0]
        target_picker.location = end_spot[1]
        #定位picker的最终位置
        #拣选员的行走距离
        self.walking_distance.append(PickingTime* v_picker +picker_Traveldis_1stspot)
        #总拣选时间=行走时间+拣选单个订单的时间
        yield self.timeout(PickingTime + pTperItem * NUM_OF_ORDERS)
        #释放拣选员资源
        self.pickers.put(target_picker)
        #机器人回到depot
        robot_BacktoDepot = get_distance(end_spot, [12, 0]) / v_robot
        yield self.timeout(robot_BacktoDepot)
        #释放机器人资源
        self.robots.put(target_machine)
        #计算分拣时间
        yield self.timeout(sTperItem * NUM_OF_ORDERS)
        #计算总处理时间
        self.total_time.append(self.now - arrive_time)
        #计算服务时间（包括行走拣选时间，回到depot时间，前往start point时间，拣选货物时间，分拣货物时间）
        serve_time = PickingTime + robot_BacktoDepot + TravelTime_1stspot + pTperItem * NUM_OF_ORDERS + sTperItem * NUM_OF_ORDERS
        self.serve_time.append(serve_time)
        #logging.log(10,
        #            f"{self.now:.2f}, Batch-{client_id} has left, serve_time:{serve_time:.2f}, waiting time:{waiting_time:.2f}.")
        self.served = client_id
        self.robot_queue_record[0] += 1
        self.robot_queue_record[1] += len(self.robots.get_queue)

        #计算疲劳度,tempt人机协同，tempt1纯人工

        tempt=1
        tempt1=1
        sum=0
        sum1=0
        tempt = tempt * math.e ** (-Travel_Fatigue * picker_TravelTime_1stspot)
        tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * TravelTime_1stspot)
        tempt1= tempt1 * math.e ** (-Travel_Fatigue * picker_TravelTime_1stspot)
        sum=sum+1-tempt
        sum1=sum1+1-tempt1
        for j in range(NUM_OF_ORDERS-1):
            #单次拣选增加疲劳
            tempt=tempt*math.e**(-Pick_Fatigue*pTperItem)
            tempt1=tempt1*math.e**(-Pick_Fatigue*pTperItem)

            #行走过程疲劳变化
            t_walk=self.travel_distance(orderlist[j][0],orderlist[j][1],orderlist[j+1][0],orderlist[j+1][1])/v_picker
            tempt1=tempt1*math.e**(-Travel_Fatigue * t_walk)
            #人机协同系统疲劳恢复（此时仍然需要travel）
            tempt = tempt * math.e ** (-Travel_Fatigue * t_walk)
            tempt=1-(1-tempt)*math.e**(-Recover_Rate*t_walk)
            #疲劳恢复上限为1
            if tempt>1:
                tempt=1

            sum = sum + 1 - tempt
            sum1 = sum1 + 1 - tempt1
        t_back1=get_distance(end_spot, [12, 0]) / v_picker
        t_back2 = get_distance(end_spot, [12, 0]) / v_robot
        tempt1=tempt1* math.e**(-Travel_Fatigue*t_back1)
        # 人机协同系统疲劳恢复（此时不需要travel）
        tempt=1-(1-tempt)*math.e**(-Recover_Rate*t_back2)

        sum=sum+1-tempt
        sum1=sum1+1-tempt1

        self.tempt.append(sum)
        self.tempt1.append(sum1)



    def output(self):
        meanQuelength = self.robot_queue_record[1] / self.robot_queue_record[0]
        meanWalkingDis = sum(self.walking_distance) / len(self.walking_distance)
        meanWaitingTime = sum(self.waiting_time) / len(self.waiting_time)
        meanServiceTime = sum(self.serve_time) / len(self.serve_time)
        meanTotalTime = sum(self.total_time) / len(self.total_time)
        meanFatigue1=sum(self.tempt)/len(self.tempt)#人机协同
        meanFatigue2 = sum(self.tempt1) / len(self.tempt1)#纯人工
        logging.log(50, f"{'-' * 30}\nTotal Simulation time: {SIMULATION_ELAPSE} s\n"
                        f"Arrive: {self.order_idx}\n"
                        f"Served: {self.served}\n"
                        f"Mean Queue Length:{self.robot_queue_record[1] / self.robot_queue_record[0]:.2f}\n"
                        f"Mean Walking Distance:{sum(self.walking_distance) / len(self.walking_distance):.2f} m\n"
                        f"Mean Waiting Time:{sum(self.waiting_time) / len(self.waiting_time):.2f} s\n"
                        f"Mean Service Time:{sum(self.serve_time) / len(self.serve_time):.2f} s\n"
                        f"Mean Total Time:{sum(self.total_time) / len(self.total_time):.2f} s"
                        )
        mylist = list((meanFatigue1,meanFatigue1/NUM_OF_ORDERS,meanFatigue2,meanFatigue2/NUM_OF_ORDERS,self.order_idx,self.served,meanQuelength,meanWalkingDis,meanWaitingTime,meanServiceTime,meanTotalTime))
        return mylist