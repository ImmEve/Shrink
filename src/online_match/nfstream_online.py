import statistics
from nfstream import NFStreamer, NFPlugin
from online_identification import *


class FlowFilter(NFPlugin):
    def __init__(self, offline_file, log_file):
        self.offline_file = offline_file
        self.log_file = log_file
        self.video_filter = 8
        self.result_filter = 5

    def on_init(self, packet, flow):
        flow.udps.packet_datasize = []
        flow.udps.packet_datasize.append(packet.raw_size - 40)
        flow.udps.chunk = []
        flow.udps.segment = 0
        flow.udps.result_url_list = []
        flow.udps.result_url = -1
        flow.udps.whether_video = False

    def on_update(self, packet, flow):
        flow.udps.packet_datasize.append(packet.raw_size - 34)
        if packet.src_ip == flow.src_ip and packet.raw_size - 34 > 100:
            if flow.udps.segment > 600 * 1024:
                flow.udps.chunk.append(flow.udps.segment)
                if sum(flow.udps.chunk) > self.video_filter * 1024 * 1024:
                    flow.udps.whether_video = True
                    offline_audio_thd = 600 * 1024
                    high_orders, high_bins_count, high_win_size = 5, 160, 21
                    low_orders, low_bins_count, low_win_size = 1, 160, 14
                    markov_alg = Markov_alg(flow.udps.chunk, self.offline_file, offline_audio_thd, high_orders,
                                            high_bins_count, high_win_size, low_orders, low_bins_count, low_win_size)
                    if markov_alg.pred_stream != -1 and markov_alg.pred_stream != None:
                        flow.udps.result_url_list.append(markov_alg.pred_stream.video_url)
                    if len(flow.udps.result_url_list) >= self.result_filter:
                        if flow.udps.result_url == -1:
                            flow.udps.result_url = statistics.mode(flow.udps.result_url_list)
                            with open(self.log_file, 'a') as f:
                                f.write(time.strftime('%Y.%m.%d_%H:%M\n', time.localtime(time.time())))
                                f.write(('Flow: {}.{}>{}.{}\n').format(flow.src_ip, flow.src_port, flow.dst_ip,
                                                                       flow.dst_port))
                                f.write('Found the url for the video: ' + flow.udps.result_url + '\n')
                                f.write('\n')
                        elif flow.udps.result_url != statistics.mode(flow.udps.result_url_list):
                            flow.udps.result_url = statistics.mode(flow.udps.result_url_list)
                            with open(self.log_file, 'a') as f:
                                f.write(time.strftime('%Y.%m.%d_%H:%M\n', time.localtime(time.time())))
                                f.write(('Flow: {}.{}>{}.{}\n').format(flow.src_ip, flow.src_port, flow.dst_ip,
                                                                       flow.dst_port))
                                f.write('Changed the url for the video: ' + flow.udps.result_url + '\n')
                                f.write('\n')

            flow.udps.segment = 0
        elif packet.dst_ip == flow.src_ip:
            flow.udps.segment = flow.udps.segment + packet.raw_size - 34

    def on_expire(self, flow):
        if flow.udps.whether_video and flow.udps.result_url == -1:
            with open(self.log_file, 'a') as f:
                f.write(time.strftime('%Y.%m.%d_%H:%M\n', time.localtime(time.time())))
                f.write(('Flow: {}.{}>{}.{}\n').format(flow.src_ip, flow.src_port, flow.dst_ip, flow.dst_port))
                f.write('Did not find the url for the video\n')
                f.write('\n')


def streamer(offline_file, log_file):
    streamer = NFStreamer(source='Intel(R) Ethernet Connection I217-V',
                          udps=FlowFilter(offline_file=offline_file, log_file=log_file))
    # streamer = NFStreamer(source='Intel(R) Ethernet Connection I217-V')
    return streamer


if __name__ == '__main__':
    offline_file = 'C:/Shrink/data/fingerprint/finger.csv'
    online_file = 'C:/Shrink/data/fingerprint/nfstream_online.csv'
    t = time.strftime('%m_%d_%H_%M', time.localtime(time.time()))
    log_file = 'C:/Shrink/data/result/log_' + t + '.txt'
    f = open(log_file, 'a')
    f.close()

    nf = streamer(offline_file=offline_file, log_file=log_file)
    #for stream in nf:
    #    pass
    nf.to_csv(path=online_file)
