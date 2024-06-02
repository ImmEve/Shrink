import csv
import socket
import dpkt
import matplotlib.pyplot as plt


def process_pcap(pcap, host_ip):
    flows = {}
    with open(pcap, 'rb') as f:
        r = dpkt.pcap.Reader(f)

        for ts, buf in r:
            try:
                packet = dpkt.ethernet.Ethernet(buf)
            except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                continue

            if isinstance(packet.data, dpkt.ip.IP) and hasattr(packet.data, 'udp'):
                src_ip = socket.inet_ntoa(packet.data.src)
                dst_ip = socket.inet_ntoa(packet.data.dst)
                src_port = packet.data.data.sport
                dst_port = packet.data.data.dport

                if dst_ip == host_ip and src_port == 443:
                    flow_key = (src_ip, dst_ip, src_port, dst_port)
                    if flow_key not in flows:
                        flows[flow_key] = []
                    flows[flow_key].append(packet)

    flows_list = flows.keys()
    videoflows = []
    for i in flows_list:
        sumlen = 0
        for j in flows[i]:
            sumlen = sumlen + j.data.data.ulen
        if sumlen > 10 * 1024 * 1024:
            videoflows.append(i)

    P = {}
    P_all = []
    for videoflow in videoflows:
        P[videoflow] = []

    with open(pcap, 'rb') as f:
        r = dpkt.pcap.Reader(f)
        ind = 0
        for ts, buf in r:
            ind += 1

            try:
                packet = dpkt.ethernet.Ethernet(buf)
            except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                continue

            if isinstance(packet.data, dpkt.ip.IP) and hasattr(packet.data, 'udp'):
                p = {}
                p['src_ip'] = socket.inet_ntoa(packet.data.src)
                p['dst_ip'] = socket.inet_ntoa(packet.data.dst)
                p['src_port'] = packet.data.data.sport
                p['dst_port'] = packet.data.data.dport
                p['time'] = ts
                p['datalen'] = packet.data.data.ulen

                flag = 0
                for videoflow in videoflows:
                    if (p['src_ip'], p['dst_ip'], p['src_port'], p['dst_port']) == videoflow or (
                            p['dst_ip'], p['src_ip'], p['dst_port'], p['src_port']) == videoflow:
                        P[videoflow].append(p)
                        flag = 1
                if flag == 1:
                    P_all.append(p)

    return P, videoflows, P_all


def request_chunk(P, host_ip):
    chunk_list = []
    len_P = len(P)
    sum = 0
    for i in range(len_P):
        if P[i]['src_ip'] == host_ip:
            if P[i]['datalen'] > 100:
                chunk_list.append(sum)
                sum = 0
        else:
            sum = sum + P[i]['datalen']
    video = []
    audio = []
    for i in chunk_list:
        if i < 600 * 1024:
            audio.append(i)
        else:
            video.append(i)
    return video


def write_offline(datapath, file, host_ip, content, offlinefile):
    _content = content[:]
    s_videoflows = ''
    try:
        P, videoflows, P_all = process_pcap(datapath + 'pcap/' + file + '.pcap', host_ip)
    except:
        _content[7] = s_videoflows
        _content[14] = s_videoflows
        _content.remove(_content[4])
        _content.remove(_content[4])
        return 
    for videoflow in videoflows:
        s_videoflows = s_videoflows + '/{}.{}>{}.{}'.format(videoflow[1], videoflow[3], videoflow[0], videoflow[2])

    if s_videoflows != '':
        _content[7] = s_videoflows
        _content[14] = s_videoflows
        _content.remove(_content[4])
        _content.remove(_content[4])

        with open(offlinefile, 'a', encoding='utf-8') as f:
            for i in range(len(_content)):
                f.write(_content[i])
                if i < len(_content) - 1:
                    f.write(',')
            f.write('\n')


def write_onlie(datapath, file, host_ip, onlinefile):
    with open(datapath + 'url/' + file, 'r', encoding='utf-8') as f1:
        url = f1.read()
    url = url.split(',')[0]
    P, videoflows, P_all = process_pcap(datapath + 'pcap/' + file + '.pcap', host_ip)
    for videoflow in videoflows:
        video = request_chunk(P[videoflow], host_ip)
        if len(video) >= 10:
            with open(onlinefile, 'a', encoding='utf-8') as f:
                f.write(url + ',')
                f.write('{}.{}>{}.{},'.format(videoflow[1], videoflow[3], videoflow[0], videoflow[2]))
                for chunk in video:
                    f.write(str(chunk) + '/')
                f.write('\n')


if __name__ == '__main__':
    host_ip = '192.168.32.38'
    tmpfile = 'C:/Shrink/data/temp/tmp_finger.csv'
    datapath = 'C:/Shrink/data/record/test/'
    offlinefile = 'C:/Shrink/data/fingerprint/finger.csv'
    onlinefile = 'C:/Shrink/data/fingerprint/online.csv'

    with open(tmpfile, 'r') as f:
        reader = csv.reader(f)
        txt = list(reader)
    len_txt = len(txt)

    for i in range(len_txt):
        file = txt[i][7].replace('/', '')
        write_offline(datapath, file, host_ip, txt[i], offlinefile)
        write_onlie(datapath, file, host_ip, onlinefile)