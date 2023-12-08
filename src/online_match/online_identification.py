import math
import time
from collections import deque


class Video_flow():
    def __init__(self, finger_list, tuple_list, video_url='', mitm_path='', streamID=-1,
                 state_transition_matrix='') -> None:
        # 指纹列表
        self.finger_list = finger_list
        # 传输使用的五元组列表
        self.tuple_list = tuple_list
        # 视频对应的URL
        self.video_url = video_url
        self.mitm_path = mitm_path
        self.state_transition_matrix = state_transition_matrix
        self.streamID = streamID


class Offline_Process():
    def __init__(self, offline_file, offline_audio_thd=700000) -> None:
        self.offline_file = offline_file
        self.offline_audio_thd = offline_audio_thd
        self.offline_chunk_list = []
        self.get_offline_finger()
        self.small_chunk_clean(self.offline_chunk_list, offline_audio_thd)

    # 获取离线指纹
    def get_offline_finger(self):
        offline_file = open(self.offline_file, mode='r', encoding='utf-8')
        offline_data = offline_file.read()
        offline_datas = offline_data.split('\n')
        streamID = -1
        for lines in offline_datas:
            if lines == '':
                continue
            vals = lines.split(',')
            video_url = vals[3]  # 视频URL
            stream_type = vals[2]  # video or audio
            finger = vals[4].split('/')[1:]  # 指纹
            tuples = vals[5].split('/')[1:]  # 五元组
            mitm_path = vals[0]  # mitm_path路径
            if stream_type == 'video':
                streamID += 1
                video_flow = Video_flow(list(map(int, finger)), tuples, video_url, mitm_path, streamID)
                self.offline_chunk_list.append(video_flow)
            if stream_type == 'audio':
                pass

    # 过滤掉指纹序列中小于阈值的块
    def small_chunk_clean(self, chunk_list, audio_thd):
        for chunk in chunk_list:
            clean_finger = []
            for val in chunk.finger_list:
                if val > audio_thd:
                    clean_finger.append(val)
            chunk.finger_list = clean_finger


class Markov_alg():
    def __init__(self, online_chunk_list, offline_file, offline_audio_thd, high_orders, high_bins_count, high_win_size,
                 low_orders, low_bins_count, low_win_size) -> None:

        self.video_chunk_size_max = 2200000.0
        self.video_chunk_size_min = offline_audio_thd
        # 获取指纹数据
        finger_data = Offline_Process(offline_file, offline_audio_thd)
        self.offline_chunk_list = finger_data.offline_chunk_list
        self.online_chunk_list = online_chunk_list

        self.high_glabal_state_transition_table = self.state_transition_calculate(high_bins_count, high_orders)
        self.high_state_transition_table = self.state_transition_table_generate(high_orders)
        self.low_glabal_state_transition_table = self.state_transition_calculate(low_bins_count, low_orders)
        self.low_state_transition_table = self.state_transition_table_generate(low_orders)

        self.pred_stream = None
        self.zero_prob = 0
        self.online_match(high_orders, high_bins_count, high_win_size, 0)
        self.streamID2video_flow_class()
        self.online_match(low_orders, low_bins_count, low_win_size, 1)
        self.streamID2video_flow_class()

    # 记录指纹库的所有转移概率
    def state_transition_calculate(self, bins_count, orders):
        global_tran_prob_table = {}
        word_count = 0
        orders += 1
        # 计算离线指纹的order阶概率转移矩阵
        index_i = -1
        bin_size = (self.video_chunk_size_max - self.video_chunk_size_min) / bins_count
        for offline_chunk in self.offline_chunk_list:
            index_i += 1
            self.offline_chunk_list[index_i].state_transition_matrix = ''
            # 用一个队列记录n阶的桶关系
            bin_relation_que = deque()
            state_transition_dict = {}
            for chunk in offline_chunk.finger_list:
                # 离线 等分分桶
                # 获得桶的编号
                if chunk >= self.video_chunk_size_max:
                    bin_index_cur = bins_count - 1
                elif chunk <= self.video_chunk_size_min:
                    bin_index_cur = 0
                else:
                    bin_index_cur = int((chunk - self.video_chunk_size_min) / bin_size)
                # 记录转移序列
                bin_relation_que.append(bin_index_cur)
                if len(bin_relation_que) < orders:
                    continue
                relation_key = ''
                for val in bin_relation_que:
                    relation_key += str(val) + '-'
                if relation_key not in state_transition_dict:
                    state_transition_dict[relation_key] = 1
                else:
                    state_transition_dict[relation_key] += 1

                # 全局概率
                if relation_key not in global_tran_prob_table:
                    global_tran_prob_table[relation_key] = 1
                else:
                    global_tran_prob_table[relation_key] += 1
                word_count += 1

                bin_relation_que.popleft()
            self.offline_chunk_list[index_i].state_transition_matrix = state_transition_dict

        for transition, transition_prob in global_tran_prob_table.items():
            prob = math.log(word_count / (transition_prob + 1))
            global_tran_prob_table[transition] = prob
        return global_tran_prob_table

    # 生成指纹库的转移概率表
    def state_transition_table_generate(self, orders):
        state_transition_table = {}
        for offline_chunk in self.offline_chunk_list:
            cur_state_transition_dict = offline_chunk.state_transition_matrix
            off_chunk_len = len(offline_chunk.finger_list)
            if cur_state_transition_dict == '' or len(cur_state_transition_dict) == 0:
                continue
            cur_streamID = offline_chunk.streamID
            for transition, transition_prob in cur_state_transition_dict.items():
                transition_prob = transition_prob / (off_chunk_len + 1 - orders)
                if transition in state_transition_table:
                    state_transition_table[transition].append([cur_streamID, transition_prob])
                else:
                    state_transition_table[transition] = [[cur_streamID, transition_prob]]
        return state_transition_table

    # 在线匹配
    def online_match(self, orders, bins_count, win_size, mutil_order_flag):
        time_sum = 0
        time_count = 0
        orders += 1
        bin_size = (self.video_chunk_size_max - self.video_chunk_size_min) / bins_count
        # 长度太短而不参与匹配的在线指纹数量
        if mutil_order_flag == 0:
            state_transition_table = self.high_state_transition_table
            # global
            global_state_transition_table = self.high_glabal_state_transition_table
        else:
            state_transition_table = self.low_state_transition_table
            # global
            global_state_transition_table = self.low_glabal_state_transition_table

        # 马尔可夫降阶
        if mutil_order_flag == 1:
            if self.zero_prob == 0:
                return 0
        else:
            self.pred_stream = None

        online_chunk = self.online_chunk_list
        online_bin_relation_que = deque()
        online_state_transition_dict = {}
        # 长度太短而不参与匹配,+n则保证至少有n次转移
        if len(online_chunk) < orders + 1:
            return 0
        time_start = time.time()
        ##在线指纹预处理：计算转移过程
        on_chunk_count = 0
        for on_chunk in online_chunk:
            # 动态偏置
            chunk_bias = on_chunk * 0.97214644 - 1145.44281353
            if chunk_bias >= self.video_chunk_size_max:
                bin_index_cur = bins_count - 1
            elif chunk_bias <= self.video_chunk_size_min:
                bin_index_cur = 0
            else:
                bin_index_cur = int((chunk_bias - self.video_chunk_size_min) / bin_size)

            # 记录转移序列
            online_bin_relation_que.append(bin_index_cur)
            if len(online_bin_relation_que) < orders:
                continue
            relation_key = ''
            for val in online_bin_relation_que:
                relation_key += str(val) + '-'
            if relation_key not in online_state_transition_dict:
                online_state_transition_dict[relation_key] = 1
            else:
                online_state_transition_dict[relation_key] += 1
            online_bin_relation_que.popleft()
            # 控制在线匹配指纹的长度
            on_chunk_count += 1
            if on_chunk_count >= win_size:
                break

        # 计算最大概率值对应的streamID
        state_dict = {}
        for on_key, on_val in online_state_transition_dict.items():
            if on_key in state_transition_table:
                for val in state_transition_table[on_key]:
                    if val[0] in state_dict:
                        # state_dict[val[0]] += on_val * val[1]
                        # state_dict[val[0]] +=on_val*val[1]*global_state_transition_table[on_key]
                        state_dict[val[0]] += on_val * val[1] + global_state_transition_table[on_key] * 100
                    else:
                        # state_dict[val[0]] = on_val * val[1]
                        # state_dict[val[0]]=on_val*val[1]*global_state_transition_table[on_key]
                        state_dict[val[0]] = on_val * val[1] + global_state_transition_table[on_key] * 100

        max_prob = 0
        target_id = -1
        if len(state_dict) == 0:
            self.zero_prob = 1
        else:
            for stream_id, prob in state_dict.items():
                if prob > max_prob:
                    max_prob = prob
                    target_id = stream_id
        self.pred_stream = target_id
        time_end = time.time()
        time_sum += time_end - time_start
        time_count += 1

    # 在线匹配过程中streamID与指纹库类的对应关系
    def streamID2video_flow_class(self):
        if self.pred_stream == -1:
            return 0
        for offline_chunk in self.offline_chunk_list:
            if offline_chunk.streamID == self.pred_stream:
                self.pred_stream = offline_chunk
