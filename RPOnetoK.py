import math

import simpy
import numpy as np
import logging
import random
import simpy
from typing import List, Tuple

from pandocfilters import Math

from MachineSetting import MachineList
from PickerSetting2 import PickerList
from Config import *

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
        self.waiting_robot: List[float] = []
        self.tempt: List[float] = []
        self.avg: List[float] = []

    def orderArrive(self):
        while True:
            time_interval = random.expovariate(ARRIVAL_RATE)
            yield self.timeout(time_interval)
            #ging.log(10, f"{self.now:.2f}, Batch-{self.order_idx} arrived")
            self.process(self.serve(self.order_idx))
            self.order_idx += 1

    def travel_distance(self, this_aisle, this_location, next_aisle, next_location) -> float:

        # 如果同巷道，直接相减
        if (next_aisle == this_aisle):
            return abs(this_location - next_location) * WIDTH_OF_SHELVES
        else:
            # 两侧距离相等
            if (NUM_OF_LOCATIONS > this_location + next_location):
                return abs(this_aisle - next_aisle) * WIDTH_OF_AISLE + (
                            this_location + next_location) * WIDTH_OF_SHELVES
            else:
                # 很近的一侧距离
                return abs(this_aisle - next_aisle) * WIDTH_OF_AISLE + (
                        2 * NUM_OF_LOCATIONS - (this_location + next_location)) * WIDTH_OF_SHELVES

    def serve(self, client_id):
        arrive_time = self.now
        random.seed(client_id)
        orderlist: list = [0] * NUM_OF_ORDERS
        arealist = [[] for _ in range(NUM_OF_AREAS)]
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

        target_machine = yield self.robots.get_robot(orderlist[0])
        getMachineTime = self.now
        waiting_time = getMachineTime - arrive_time
        self.waiting_robot.append(getMachineTime - arrive_time)
        serve_time = 0
        walking_distance = 0
        tempt_aisle: List[float] = []#用来求每个巷道拣选员疲劳度的list
        avg_aisle: List[float] = []  # 用来求每个巷道拣选员疲劳度的list
        ordersum=0

        for i in range(NUM_OF_AREAS):
            if len(arealist[i])==0:
                continue
            else:
                spot = [arealist[i][0],arealist[i][len(arealist[i])-1]]
                picker, start_spot, end_spot = self.pickers.get_picker(area=i+1,spot=spot)
                target_picker = yield picker
                distance1 = target_picker.picker_travel_distance(start_spot)
                distance2 = target_picker.picker_travel_distance(end_spot)
                if (distance2 < distance1):
                    k = start_spot
                    start_spot = end_spot
                    end_spot = k
                getPickerTime = self.now
                waiting_time += getPickerTime - getMachineTime

                #协同平行行走时间计算
                robot_TravelTime_1stspot = target_machine.robot_travel_distance(start_spot) / v_robot
                #如果拣选员和spot0不在同一巷道
                if(target_picker.aisle!=start_spot[0]):
                    picker_Traveldis_1stspot = abs(target_picker.aisle - start_spot[0]) * WIDTH_OF_AISLE + (target_picker.location + start_spot[1]) * WIDTH_OF_SHELVES
                else:
                    picker_Traveldis_1stspot = abs(target_picker.location - start_spot[1]) * WIDTH_OF_SHELVES
                picker_TravelTime_1stspot = picker_Traveldis_1stspot/v_picker
                TravelTime_1stspot = max(robot_TravelTime_1stspot, picker_TravelTime_1stspot)
                yield self.timeout(TravelTime_1stspot)

                #区域内拣选
                Picking_dis = ((2*NUM_OF_LOCATIONS - start_spot[1] - end_spot[1])*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS +
                            (aisleLimit - 2) * ((NUM_OF_LOCATIONS-1)*WIDTH_OF_SHELVES + 2*WIDTH_BETWEEN_AS)+
                           (aisleLimit - 1) * WIDTH_OF_AISLE)
                PickingTime = Picking_dis / v_picker
                yield self.timeout(PickingTime+pTperItem * len(arealist[i]))
                #更新拣选员与机器人位置
                target_picker.traveled_dis += (PickingTime+picker_TravelTime_1stspot) * v_picker
                target_picker.aisle = end_spot[0]
                target_picker.location = end_spot[1]
                target_machine.aisle = end_spot[0]
                target_machine.location = end_spot[1]
                #记录拣选员行走的距离
                walking_distance += Picking_dis + picker_Traveldis_1stspot
                yield self.pickers.put(target_picker)
                getMachineTime = self.now  #更新时间，下次等待为get下个拣选员
                serve_time += TravelTime_1stspot + PickingTime + pTperItem * len(arealist[i])

                sum1=0
                tempt = 1
                tempt = tempt * math.e ** (-Travel_Fatigue * picker_TravelTime_1stspot)
                tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * TravelTime_1stspot)
                sum1=sum1+1-tempt
                for j in range(len(arealist[i]) - 1):
                    tempt = tempt * math.e ** (-Pick_Fatigue * pTperItem)
                    # 行走过程疲劳变化
                    t_walk = self.travel_distance(arealist[i][j][0], arealist[i][j][1], arealist[i][j + 1][0],
                                                  arealist[i][j + 1][1]) / v_picker
                    tempt = tempt * math.e ** (-Travel_Fatigue * t_walk)
                    tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * t_walk)
                    if tempt > 1:
                        tempt = 1
                    sum1 = sum1 + 1 - tempt

                ordersum = ordersum + len(arealist[i])
                if i==NUM_OF_AREAS-1 or ordersum==NUM_OF_ORDERS:
                    t_cross = self.travel_distance(orderlist[ordersum - 1][0], orderlist[ordersum - 1][1],
                                                   1/2*NUM_OF_AISLES, 0) / v_robot
                else:
                    t_cross = self.travel_distance(orderlist[ordersum - 1][0], orderlist[ordersum - 1][1],
                                               orderlist[ordersum][0], orderlist[ordersum][1]) / v_robot
                # 最后一个订单原地休息
                tempt = 1 - (1 - tempt) * math.e ** (-Recover_Rate * t_cross)
                if tempt > 1:
                    tempt = 1
                sum1 = sum1 + 1 - tempt
                tempt_aisle.append(sum1)
                avg_aisle.append(sum1/len(arealist[i]))

        self.tempt.append(sum(tempt_aisle)/len(tempt_aisle))
        self.avg.append(sum(avg_aisle) / len(avg_aisle))


        robot_BacktoDepot = target_machine.robot_travel_distance([1/2*NUM_OF_AISLES, 0]) / v_robot
        yield self.timeout(robot_BacktoDepot)
        target_machine.aisle = 1/2*NUM_OF_AISLES
        target_machine.location = 0
        self.robots.put(target_machine)
        yield self.timeout(sTperItem * NUM_OF_ORDERS)
        self.waiting_time.append(waiting_time)
        self.walking_distance.append(walking_distance)
        serve_time += robot_BacktoDepot + sTperItem * NUM_OF_ORDERS
        self.serve_time.append(serve_time)
        self.total_time.append(self.now - arrive_time)
        #logging.log(10, f"{self.now:.2f}, Batch-{client_id} has left, serve_time:{serve_time:.2f}, waiting time:{waiting_time:.2f}.")
        self.served = client_id
        self.robot_queue_record[0] += 1
        self.robot_queue_record[1] += len(self.robots.get_queue)


    def output(self):
        meanQuelength = self.robot_queue_record[1] / self.robot_queue_record[0]
        meanWalkingDis = sum(self.walking_distance) / self.served
        meanWaitingTime = sum(self.waiting_time) / len(self.waiting_time)
        meanServiceTime = sum(self.serve_time) / len(self.serve_time)
        meanWaitingTime2 = sum(self.waiting_time) / self.served
        meanServiceTime2 = sum(self.serve_time) / self.served
        meanTotalTime = sum(self.total_time) / len(self.total_time)
        meanFatigue=sum(self.tempt)/len(self.tempt)
        avgFatigue=sum(self.avg)/len(self.avg)
        logging.log(50, f"{'-' * 30}\nTotal Simulation time: {SIMULATION_ELAPSE} s\n"
                        f"Arrive: {self.order_idx}\n"
                        f"Served: {self.served}\n"
                        f"Mean Queue Length:{self.robot_queue_record[1] / self.robot_queue_record[0]:.2f}\n"
                        f"Mean Walking Distance:{sum(self.walking_distance) / self.served:.2f} m\n"
                        f"Mean Waiting Time:{sum(self.waiting_time) / len(self.waiting_time):.2f} s\n"
                        f"Mean Waiting robot:{sum(self.waiting_robot) / len(self.waiting_robot):.2f} s\n"
                        f"Mean Service Time:{sum(self.serve_time) / len(self.serve_time):.2f} s\n"
                        f"Mean Total Time:{sum(self.total_time) / len(self.total_time):.2f} s"
                        )
        mylist = list((meanFatigue,avgFatigue,self.order_idx,self.served,meanQuelength,meanWalkingDis,meanWaitingTime,meanServiceTime,meanTotalTime))
        return mylist