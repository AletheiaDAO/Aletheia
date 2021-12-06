from aletheia.artificial_system import ArtificalSystem, duet
import numpy as np
from aletheia.utils.constant import  *
# from pargov.gnosystem import GNOSystem


class InforAgent(object):

    def __init__(self, unique_id: int, model: ArtificalSystem, u_yes=0.5, u_no = 0.5, risk_coeff=0, available=1, vote_day =0, states={}, beta_a=3, beta_b=3, belief_reliable_up=1, belief_reliable_down=0, vote_choice=1) -> None:

        self.unique_id = unique_id
        self.model = model
        self.belief = {}
        self.tradded =  False  # flag for last sell/buy
        self.u_yes = u_yes
        self.u_no = u_no
        self.risk_coeff = risk_coeff

        middle_reliable = (belief_reliable_up + belief_reliable_down) / 2
        if self.risk_coeff > 0:
            self.info_reliable = np.random.uniform(middle_reliable,  belief_reliable_up)
        elif self.risk_coeff == 0:
            self.info_reliable = middle_reliable
        else:
            self.info_reliable = np.random.uniform(belief_reliable_down, middle_reliable)

        self.available = available
        self.vote_day = vote_day
        self.states = states
        # self.beta_a = 3
        # self.beta_b = 
        self.beta_a = beta_a
        self.beta_b = beta_b
        self.init_GNO = self.states[GNO]
        self.init_DAI = self.states[DAI]
        self.vote_choice = vote_choice

    def observe(self):
        for proposal in self.model.activate_proposals:
            for accept_token in [GNO, DAI]:
                yes_token = '{}_{}_YES'.format(proposal._id, accept_token)
                no_token = '{}_{}_NO'.format(proposal._id, accept_token)

                if yes_token not in self.states.keys():
                    self.states[yes_token] = 0
                if no_token not in self.states.keys():
                    self.states[no_token] = 0
            if proposal._id not in self.belief.keys():
                self.belief[proposal._id] = np.random.beta(self.beta_a, self.beta_b)

    def update_belief_with_price(self, price, proposal_id):
        if self.tradded:
            u = self.u_yes
        else:
            u = self.u_no

        self.belief[proposal_id] = self.belief[proposal_id] * u + (1 - u) * price

    def update_belief_with_info(self, info, proposal_id):
        self.belief[proposal_id] = self.info_reliable * ( self.belief[proposal_id] - info * np.log(self.belief[proposal_id])) + (1 - self.info_reliable) * self.belief[proposal_id]
        # print('debug')

    def compute_utility_function_trade(self, accet_token):
        # w = self.states[accet_token]

        w = self.current_wealth()
        if accet_token == DAI:
            w = w[0]
        else:
            w = w[1]
        
        if self.risk_coeff == 1:
            u_n_d = np.log(w)
        else:
            u_n_d = (w ** (1 - self.risk_coeff)) / (1 - self.risk_coeff)
        # return u_n_d
        # self.utility_fc_trade = u_n_d
        return u_n_d

    def compute_utility_function_vote(self, choose='yes', price_after=1, proposal_id =None, accept_token=GNO):
        if choose == 'yes':
            return self.states[GNO] + self.states['{}_{}_YES'.format(proposal_id, accept_token)]
        else:
            return self.states[GNO] + self.states['{}_{}_NO'.format(proposal_id, accept_token)]

    def compute_Q(self, token_type=YES_TOKEN, proposal_id=None, accept_token=DAI):
        proposal = self.model.get_proposal_by_id(proposal_id)
        if not proposal:
            return

        price = self.model.get_token_price(proposal._id, token_type, accept_token)

        if self.risk_coeff == 0:
            theta_1 = 1
        else:
            theta_1 = 1 / self.risk_coeff
        
        if theta_1 >= 3:
            theta_1 = 3
        elif theta_1 <= -3:
            theta_1 = -3

        belief = self.belief[proposal_id]

        up_part_1 = ((1 - price) ** (1 / theta_1)) * (belief ** (theta_1))
        up_part_2 = ((price) ** (1/ theta_1)) * ((1 - belief) ** (1 / theta_1))

        # up_part = ((1 - price) ** (1 / self.risk_coeff)) * (belief ** (1/self.risk_coeff)) - ((price) ** (1 / self.risk_coeff)) * (( 1 - belief) ** (1 /self.risk_coeff))

        # prevent too big data

        up_part = up_part_1 - up_part_2

        down_part = (1 - price)* (price ** theta_1)*((1  - belief) ** theta_1) + price * ((1 - price) ** theta_1) * (belief ** theta_1)

        return (up_part * self.compute_utility_function_trade(accept_token)) / down_part

    def current_wealth(self):
        total_DAI = 0 
        total_GNO = 0
        for proposal in self.model.activate_proposals:
            for accept_token in [GNO, DAI]:
                yes_token = '{}_{}_YES'.format(proposal._id, accept_token)
                no_token = '{}_{}_NO'.format(proposal._id, accept_token)
                price_yes_token = self.model.get_token_price(proposal._id, YES_TOKEN, accept_token)
                price_no_token = self.model.get_token_price(proposal._id, NO_TOKEN, accept_token)
                if accept_token == GNO:
                    total_GNO += price_no_token * self.states[no_token]  + price_yes_token * self.states[yes_token]

                else:
                    total_DAI += price_no_token * self.states[no_token]  + price_yes_token * self.states[yes_token]

        total_GNO += self.states[GNO]
        total_DAI += self.states[DAI]
        return total_DAI, total_GNO

    def total_wealth(self):
        total_DAI = 0 
        total_GNO = 0
        for proposal in self.model.finished_proposals:
            for accept_token in [GNO, DAI]:
                yes_token = '{}_{}_YES'.format(proposal._id, accept_token)
                no_token = '{}_{}_NO'.format(proposal._id, accept_token)
                # price_yes_token = self.model.get_token_price(proposal._id, YES_TOKEN, accept_token)
                # price_no_token = self.model.get_token_price(proposal._id, NO_TOKEN, accept_token)
                price_yes_token = 1 if proposal.passed else 0
                price_no_token = 1 if not proposal.passed else 0
                if proposal.passed:
                    self.states[accept_token] += self.states[yes_token]
                    self.states[yes_token] =  0
                else:
                    self.states[accept_token] += self.states[no_token]
                    self.states[no_token] = 0
                if accept_token == GNO:
                    total_GNO += price_no_token * self.states[no_token]  + price_yes_token * self.states[yes_token]

                else:
                    total_DAI += price_no_token * self.states[no_token]  + price_yes_token * self.states[yes_token]

        total_GNO += self.states[GNO]
        total_DAI += self.states[DAI]
        return total_DAI, total_GNO


    def step(self):
        # self.observe()
        def ask_buy(proposal_id, token_type, amount, accept_token):
            price = self.model.get_token_price(proposal_id, token_type, accept_token)

            if token_type == NO_TOKEN:
                belief = 1 - self.belief[proposal_id]
            else:
                belief = self.belief[proposal_id]

            if price <= belief:
                self.model.buy(self, proposal_id, token_type, amount, accept_token)
                self.tradded = True

                # print('agent {} buy {} {} at price {} with token {}'.format(self.unique_id, token_type, amount, price, accept_token))
                # price = self.model.get_token_price(proposal_id, token_type, accept_token)
                # print('after buy the price became {}'.format(price))
        
        def ask_sell(proposal_id, token_type, amount, accept_token, condier_price=True):
            price = self.model.get_token_price(proposal_id, token_type, accept_token)

            if token_type == NO_TOKEN:
                belief = 1 - self.belief[proposal_id]
            else:
                belief = self.belief[proposal_id]

            if price >= belief or not condier_price:
                self.model.sell(self, proposal_id, token_type, amount, accept_token)
                self.tradded = True

                # print('agent {} sell {} {} at price {} with token {}'.format(self.unique_id, token_type, amount, price, accept_token))


        for proposal in self.model.activate_proposals:

            self.tradded = False
            for accept_token in [DAI, GNO]:
                q_star = self.compute_Q(proposal_id=proposal._id, accept_token=accept_token)

                yes_token = '{}_{}_YES'.format(proposal._id, accept_token)
                no_token = '{}_{}_NO'.format(proposal._id, accept_token)

                yes_amount = q_star - self.states[yes_token]

                if yes_amount >  1:
                    if self.states[no_token] > 0 :
                        # self.model.sell(self, proposal._id, NO_TOKEN, self.states[no_token], accept_token)
                        ask_sell(proposal._id, NO_TOKEN, self.states[no_token], accept_token, False)

                    # self.model.buy(self, proposal._id, YES_TOKEN, yes_amount, accept_token)
                    ask_buy(proposal._id, YES_TOKEN, yes_amount, accept_token)
        
                elif q_star < -1:
                    if self.states[yes_token]> 0:
                        # self.model.sell(self, proposal._id, YES_TOKEN, self.states[yes_token], accept_token)
                        ask_sell(proposal._id, YES_TOKEN, self.states[yes_token], accept_token, False)

                    ask_buy(proposal._id, NO_TOKEN, -q_star, accept_token)

                    # self.model.buy(self, proposal._id, NO_TOKEN, -q_star, accept_token)
                elif yes_amount < 1:
                    # sell_yes_token(target._id, - yes_amount)
                    # self.model.sell(self, proposal._id, YES_TOKEN, - yes_amount, accept_token)
                    ask_sell(proposal._id, YES_TOKEN, - yes_amount, accept_token)
               

                price = self.model.get_token_price(proposal._id, YES_TOKEN, accept_token)

                # self.update_belief_with_price(price, proposal._id)

                if self.vote_day == proposal.dura_time:
                    # yes_be = self.compute_utility_function_vote('yes', proposal_id=proposal._id, accept_token=accept_token)

                    # no_be = self.compute_utility_function_vote('no', proposal_id=proposal._id, accept_token=accept_token)

                    # if yes_be >= no_be:
                    if self.vote_choice == 1:
                        self.model.vote_yes(self, proposal._id)

                    elif self.vote_choice == 2:
                        self.model.vote_no(self, proposal._id)
                    else:
                        raise Exception('unkown choice')