# from aletheia.agents.property import token_cost
from aletheia.utils.constant import FEES, TRADES
import math
from enum import Enum
from aletheia.agents.agent import Agent
from aletheia.utils.constant import *
from copy import deepcopy


class TokenType(Enum):
    yes_token = 'yes_token'
    no_token = 'no_token'


class PredictMarket(object):
    def __init__(self) -> None:
        super().__init__()
        self.proposals = []

    def buy(self, agent):
        pass

    def sell(self, agent):
        pass

    def observe(self, agent):
        pass


class UniswapFPMM:
    def __init__(self, token1, token2, init_states=None, uniswap=None, fee=0.003):
        """
        init_states= {
            TRADES: [],
            LP: math.sqrt(119464 * 600632),
            FEES: {DUET:0, USDT:0},
            POOL: { DUET: 119464, USDT: 600632},
            APY: 64363.5592,
            APR: 11.0723
        }

        """
        self.token1 = token1
        self.token2 = token2

        self.states = init_states
        self.prop = init_states[POOL][token1] / init_states[POOL][token2]
        self.name = "{}_{}".format(token1, token2)
        self.fee = fee
        self.lp_constant = 0
        self.constant = init_states[POOL][token1] * init_states[POOL][token2]
        self.states[APY_WITH_REWARD] = 0
        self.states[APR_WITH_REWARD] = 0
        self.states[UNISWAP_FARM_REWARD] = 0
        self.states[LP_AMOUNT] = 1
        self.history_states = []
        # self.oracle = oracle # for apy and apr
        self.uniswap = uniswap # for apy and apr

    def farm(self, agent: Agent, amount1: float, amount2: float, fee: float):
        if self.states[POOL][self.token2] == 0:
            self.prop = 0
        self.prop = self.states[POOL][self.token1] / self.states[POOL][self.token2]
        if self.prop == 0:
            print('debug')
        expect_a2 = amount1 / self.prop
        if expect_a2 > amount2:
            amount1 = amount2 * self.prop

        else:
            amount2 = expect_a2

        if amount1 <=0 or amount2<=0:
            return False, False

        if agent.states[self.token1] >= amount1 and agent.states[self.token2] >= amount2:
            lp_states = self.states
            lp_amount_origin = self.states[LP_AMOUNT]
            lp_states[POOL][self.token1] += amount1
            lp_states[POOL][self.token2] += amount2
            lp_amount = amount1 / lp_states[POOL][self.token1]
            lp_amount = lp_amount *  lp_amount_origin
            if lp_amount <=0:
                lp_amount = 0

            self.states[LP_AMOUNT] = lp_amount_origin + lp_amount
            lp_amount_dec = round(lp_amount, 4)
            if lp_amount_dec > lp_amount:
                lp_amount_dec -= 0.0001
            
            agent.states[self.name] +=  lp_amount
            agent.states[self.token1] -= amount1
            agent.states[self.token2] -= amount2
            # self.fee = fee
            lp_states[LP] = lp_amount_origin + lp_amount

            if lp_states[POOL][self.token2] == 0:
                print('zero')
            self.prop = lp_states[POOL][self.token1] / \
                lp_states[POOL][self.token2]

            return lp_amount, {self.token1: amount1, self.token2: amount2}
        else:
            return False, False

    def withdraw(self, agent, lp_amount):
        ratio = lp_amount / self.states[LP_AMOUNT]

        if agent.states[self.name] >= lp_amount:
            amount1 = self.states[POOL][self.token1] * ratio
            amount2 = self.states[POOL][self.token2] * ratio
            self.states[LP_AMOUNT] -= lp_amount
            self.states[POOL][self.token1] -= amount1
            self.states[POOL][self.token2] -= amount2
            agent.states[self.token1] += amount1
            agent.states[self.token2] += amount2
            agent.states[self.name] -= lp_amount
            return {self.token1 : amount1, self.token2: amount2}
        else:
            return False

    def decade_liquity(self, factor):
        pass


    def evaluate_swap(self, origin_token, amount):
        # if self.constant == 0:
            # return False

        if origin_token == self.token1:
            true_amount = amount / (1 + self.fee)
            val = self.calc_price(true_amount, 0)
            return val
        else:
            true_amount = amount / (1 + self.fee)
            val = self.calc_price(0, true_amount)
            return val
    
    def swap(self, agent: Agent, origin_token, amount, with_fee=True):
        """
        amount is the input amount
        """
        # if self.constant == 0:
        #     return False
        if amount <= 0:
            return False

        # if self.states[POOL][self.token1] * self.current_price(self.token1) <=100 or self.states[POOL][self.token2] * self.current_price(self.token2) <= 0.01: # too low liqudity
            # return False

        if origin_token == self.token1:
            if with_fee:
                true_amount = amount / (1 + self.fee)
                fee = true_amount * self.fee
            else:
                true_amount = amount

            cost = amount
            if agent.states[origin_token] >= cost:
                val = self.calc_price(true_amount, 0)
                agent.states[origin_token] -= cost
                ### for verify the mius number
                if agent.states[origin_token] < 0:
                    print('something is wrong')
                    print(cost)
                    print(agent.states[origin_token])
                    agent.states[origin_token] = 0

                agent.states[self.token2] += val
                if with_fee:
                    self.states[FEES][origin_token] += fee
                self.states[POOL][origin_token] += cost
                self.states[POOL][self.token2] -= val
                if val == 0:
                    return False
                return val
            else:
                return False
        else:
            if with_fee:
                true_amount = amount / (1 + self.fee)
                fee = true_amount * self.fee
            else:
                true_amount = amount

            cost = amount
            if agent.states[origin_token] >= cost:
                val = self.calc_price(0, true_amount)
                agent.states[origin_token] -= cost
                if agent.states[origin_token] < 0:
                    print('something to do')
                    print(cost)
                    print(agent.states[origin_token])
                    agent.states[origin_token] =0

                agent.states[self.token1] += val
                if with_fee:
                    self.states[FEES][origin_token] += fee
                # self.states[POOL][origin_token] += fee
                self.states[POOL][origin_token] += cost
                self.states[POOL][self.token1] -= val
                if val == 0:
                    return False
                return val
            else:
                return False

    def calc_price(self, token1, token2):
        p_w = self.states[POOL][self.token1]
        p_l = self.states[POOL][self.token2]
        constant = p_w * p_l

        yes_token = token1
        no_token = token2
        val = 0

        if yes_token:
            delta_x = yes_token
            x_1 = p_w + delta_x
            delta_y = p_l - constant/x_1
            val = delta_y

        elif no_token:
            delta_x = no_token
            x_1 = p_l + delta_x
            delta_y = p_w - constant/x_1
            val = delta_y
        return val

    def current_price(self, target_token):
        p_w = self.states[POOL][self.token1]
        p_l = self.states[POOL][self.token2]

        if target_token == self.token1:
            # return self.calc_price(1, 0)
            return p_l/p_w
        else:
            return p_w/p_l
            # return self.calc_price(0, 1)

    def get_prop(self):
        return self.prop

    def get_fee(self, amount):
        return amount * self.fee

    def add_reward(self, amount):
        self.states[UNISWAP_FARM_REWARD] += amount

    def step(self):
        self.states[POOL][POOLVALUE] = self.states[POOL][self.token1] * self.uniswap.get_usdt_price(self.token1) + \
                self.states[POOL][self.token2] * self.uniswap.get_usdt_price(self.token2)
        self.states[FEES][FEEVALUE] =   self.states[FEES][self.token1] * self.uniswap.get_usdt_price(self.token1) + \
                self.states[FEES][self.token1] * self.uniswap.get_usdt_price(self.token2)
    
        if self.history_states:
            # not include the 
            last_states = self.history_states[-1]
            token1 = last_states[POOL][self.token1]
            token2 = last_states[POOL][self.token2]
            pool_value = token1 * self.uniswap.get_usdt_price(self.token1) + token2 * self.uniswap.get_usdt_price(self.token2)

            token1_fee = self.states[FEES][self.token1] - last_states[FEES][self.token1]
            token2_fee = self.states[FEES][self.token2] - last_states[FEES][self.token2]
            pool_fee = token1_fee * self.uniswap.get_usdt_price(self.token1) + token2_fee * self.uniswap.get_usdt_price(self.token2)


            interest_rate = pool_fee / pool_value

            self.states[APR] = interest_rate * 365
            self.states[APY] = (1 + interest_rate) ** 365 - 1

            try:

                reward =  self.states[UNISWAP_FARM_REWARD] - last_states[UNISWAP_FARM_REWARD]
                interest_rate = (reward + pool_fee) / pool_value
                self.states[APR_WITH_REWARD] = interest_rate * 365
                self.states[APY_WITH_REWARD] = (1 + interest_rate) ** 365 -1
            except:
                self.states[APY_WITH_REWARD] = 100000000000
                #  self.states[APR_WITH_REWARD] = interest_rate * 365
       
        last_states = deepcopy(self.states)
        self.history_states.append(last_states)
        # self.states[UNISWAP_FARM_REWARD] = 0
        # to compute the apy and apr

    def get_pool_value(self):
        return self.states[POOL][self.token1] * self.uniswap.get_usdt_price(self.token1) + \
                self.states[POOL][self.token2] * self.uniswap.get_usdt_price(self.token2)

    def get_lp_value(self, lp_amount):
        # lp_constant = math.sqrt(
        #     self.states[POOL][self.token1] * self.states[POOL][self.token2]
        # )
        
        ratio = lp_amount /self.states[LP_AMOUNT]
        amount1 = self.states[POOL][self.token1] * ratio
        amount2 = self.states[POOL][self.token2] * ratio
        return amount1 * self.uniswap.get_usdt_price(self.token1) + amount2 * self.uniswap.get_usdt_price(self.token2)
