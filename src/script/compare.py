import csv
import os
import socket
import dpkt
import matplotlib.pyplot as plt


def getData(filepath):
    filelist = os.listdir(filepath)
    data = {}
    for filename in filelist:
        with open(filepath + filename, 'r') as f:
            txt = f.read()
        url = txt.replace('/n', '')
        data[url] = {'filename': filename, 'chunklist': [], 'channel': []}
    urllist = list(data.keys())
    with open('finger.csv', 'r') as f:
        reader = csv.reader(f)
        txt = list(reader)
    for i in txt:
        if i[3] in urllist and i[2] == 'video':
            chunklist = i[4].split('/')[1:]
            chunklist = [int(i) for i in chunklist if int(i) > 10000]
            if chunklist not in data[i[3]]['chunklist'] and len(chunklist) > 10:
                data[i[3]]['chunklist'].append(chunklist)
                data[i[3]]['channel'].append(i[11])
    file2url = {}
    for i in urllist:
        file2url[data[i]['filename']] = i
    return data, file2url


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


def write_finger(pcappath, host_ip, tmpfile, fingerfile):
    with open(tmpfile, 'r') as f:
        reader = csv.reader(f)
        txt = list(reader)
    key = {}
    for i in txt:
        pcap = i[0].split('/')[-1]
        fingerprint = i[6].split('/')[1:]
        key[pcap] = [int(j) for j in fingerprint if int(j) > 600 * 1024]

    len_txt = len(txt)
    for i in range(len_txt):
        pcap = txt[i][0].split('/')[-1]
        s_videoflows = ''
        try:
            P, videoflows, P_all = process_pcap(pcappath + pcap + '.pcap', host_ip)
        except:
            txt[i][7] = s_videoflows
            txt[i][14] = s_videoflows
            txt[i].remove(txt[i][4])
            txt[i].remove(txt[i][4])
            continue
        for videoflow in videoflows:
            s_videoflows = s_videoflows + '/{}.{}>{}.{}'.format(videoflow[1], videoflow[3], videoflow[0], videoflow[2])
        txt[i][7] = s_videoflows
        txt[i][14] = s_videoflows
        txt[i].remove(txt[i][4])
        txt[i].remove(txt[i][4])

    with open(fingerfile, 'w', encoding='utf-8') as f:
        for i in range(len_txt):
            for j in range(len(txt[i])):
                f.write(txt[i][j])
                if j < len(txt[i]) - 1:
                    f.write(',')
            f.write('\n')


def write_onlie(datapath, host_ip, onlinefile):
    videolist = os.listdir(datapath + 'url/')
    with open(onlinefile, 'w', encoding='utf-8') as f:
        for videoid in videolist:
            with open(datapath + 'url/' + videoid, 'r', encoding='utf-8') as f1:
                url = f1.read()
            url = url.split(',')[0]
            P, videoflows, P_all = process_pcap(datapath + 'pcap/' + videoid + '.pcap', host_ip)
            for videoflow in videoflows:
                video = request_chunk(P[videoflow], host_ip)
                f.write(url + ',')
                f.write('{}.{}>{}.{},'.format(videoflow[1], videoflow[3], videoflow[0], videoflow[2]))
                for chunk in video:
                    f.write(str(chunk) + '/')
                f.write('\n')


def fig_output(y1, y2, path):
    y = y1
    x = [i for i in range(len(y))]
    plt.plot(x, y, marker='o', color='black', label='$chunk_{divide}$')
    plt.legend()

    y = y2
    x = [i for i in range(len(y))]
    plt.plot(x, y, marker='v', color='red', label='$chunk_{real}$')
    plt.legend()

    plt.ylim(600 * 1024, 2097152)
    plt.xlabel('$chunk\_num$')
    plt.ylabel('$chunk\_size$')
    plt.grid()
    plt.draw()
    plt.savefig(path + '.png')
    plt.close()


if __name__ == '__main__':
    host_ip = '192.168.32.38'
    tmpfile = 'C:/Shrink/data/fingerprint/analysis_tmp.csv'
    fingerfile = 'C:/Shrink/data/fingerprint/finger.csv'
    onlinefile = 'C:/Shrink/data/fingerprint/online.csv'
    datapath = 'C:/Shrink/data/record/test/'
    write_finger(datapath + 'pcap/', host_ip, tmpfile, fingerfile)
    write_onlie(datapath, host_ip, onlinefile)
