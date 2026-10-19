package com.onryadom.wendigo;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.io.Writer;
import java.io.BufferedWriter;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.InterfaceAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Сеть для игры в одной Wi-Fi сети, без Android-зависимостей (проверяется на обычной JVM).
 * Хост: TCP-сервер на 47811 + UDP-маяк «WENDIGO|имя» на 47812 раз в секунду.
 * Гость: ловит маяки, подключается по TCP. Сообщения — строки JSON, по одной на строку.
 */
public class NetCore {
    public interface Listener { void onEvent(String type, String data); }

    public static final int TCP_PORT = 47811, UDP_PORT = 47812, MAX_LINE = 65536, MAX_PEERS = 3;
    private final Listener l;
    private volatile boolean hosting, clientOn;
    private ServerSocket server;
    private DatagramSocket beaconSock;
    private final CopyOnWriteArrayList<Peer> peers = new CopyOnWriteArrayList<Peer>();
    private volatile Peer upstream;
    private int nextId = 1;
    private String room = "";

    public NetCore(Listener l) { this.l = l; }

    final class Peer {
        final Socket s; final int id; final Writer w;
        Peer(Socket s, int id) throws IOException {
            this.s = s; this.id = id; s.setTcpNoDelay(true);
            w = new BufferedWriter(new OutputStreamWriter(s.getOutputStream(), "UTF-8"));
        }
        synchronized boolean send(String line) {
            try { w.write(line); w.write('\n'); w.flush(); return true; } catch (IOException e) { close(); return false; }
        }
        void close() { try { s.close(); } catch (IOException e) { /* уже закрыт */ } }
    }

    // ---------------------------------------------------------------- хост
    public synchronized void host(String name) {
        stop();
        room = name == null ? "" : name.replace('|', ' ').replace('\n', ' ');
        final ServerSocket ss;
        try {
            ss = new ServerSocket(); ss.setReuseAddress(true); ss.bind(new InetSocketAddress(TCP_PORT)); server = ss;
        } catch (IOException e) { l.onEvent("error", "порт " + TCP_PORT + ": " + e.getMessage()); return; }
        hosting = true;
        l.onEvent("hosting", localIp());
        daemon("net-accept", new Runnable() { public void run() {
            while (hosting) {
                try {
                    Socket s = ss.accept();
                    if (peers.size() >= MAX_PEERS) { s.close(); continue; }
                    int id; synchronized (NetCore.this) { id = ++nextId; }
                    Peer p = new Peer(s, id); peers.add(p);
                    l.onEvent("join", String.valueOf(id));
                    reader(p, true);
                } catch (IOException e) { if (hosting) l.onEvent("error", "accept: " + e.getMessage()); break; }
            }
        }});
        daemon("net-beacon", new Runnable() { public void run() { beaconLoop(); } });
    }

    private void beaconLoop() {
        DatagramSocket ds = null;
        try {
            ds = new DatagramSocket(); ds.setBroadcast(true); beaconSock = ds;
            byte[] msg = ("WENDIGO|" + room).getBytes("UTF-8");
            while (hosting) {
                for (InetAddress a : broadcastAddrs()) {
                    try { ds.send(new DatagramPacket(msg, msg.length, a, UDP_PORT)); } catch (IOException e) { /* сеть без broadcast */ }
                }
                try { Thread.sleep(1000); } catch (InterruptedException e) { break; }
            }
        } catch (IOException e) { l.onEvent("error", "beacon: " + e.getMessage()); }
        finally { if (ds != null) ds.close(); }
    }

    static List<InetAddress> broadcastAddrs() {
        List<InetAddress> out = new ArrayList<InetAddress>();
        try { out.add(InetAddress.getByName("255.255.255.255")); } catch (IOException e) { /* нет */ }
        try {
            Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces();
            while (en != null && en.hasMoreElements()) {
                NetworkInterface ni = en.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                for (InterfaceAddress ia : ni.getInterfaceAddresses()) {
                    InetAddress b = ia.getBroadcast();
                    if (b != null && !out.contains(b)) out.add(b);
                }
            }
        } catch (Exception e) { /* нет интерфейсов */ }
        return out;
    }

    // ---------------------------------------------------------------- поиск игр
    public void scan(final int ms) {
        daemon("net-scan", new Runnable() { public void run() {
            DatagramSocket ds = null; Set<String> seen = new HashSet<String>();
            try {
                ds = new DatagramSocket(null); ds.setReuseAddress(true); ds.setBroadcast(true);
                ds.bind(new InetSocketAddress(UDP_PORT)); ds.setSoTimeout(400);
                long end = System.currentTimeMillis() + ms; byte[] buf = new byte[512];
                while (System.currentTimeMillis() < end) {
                    DatagramPacket p = new DatagramPacket(buf, buf.length);
                    try {
                        ds.receive(p);
                        String s = new String(p.getData(), 0, p.getLength(), "UTF-8");
                        if (s.startsWith("WENDIGO|")) {
                            String ip = p.getAddress().getHostAddress();
                            if (seen.add(ip)) l.onEvent("found", ip + "|" + s.substring(8));
                        }
                    } catch (SocketTimeoutException e) { /* ждём дальше */ }
                }
            } catch (IOException e) { l.onEvent("error", "scan: " + e.getMessage()); }
            finally { if (ds != null) ds.close(); l.onEvent("scandone", ""); }
        }});
    }

    // ---------------------------------------------------------------- гость
    public void join(final String ip) {
        stop(); clientOn = true;
        daemon("net-join", new Runnable() { public void run() {
            try {
                Socket s = new Socket(); s.connect(new InetSocketAddress(ip, TCP_PORT), 5000);
                upstream = new Peer(s, 1);
                l.onEvent("connected", ip);
                reader(upstream, false);
            } catch (IOException e) { clientOn = false; l.onEvent("error", "подключение: " + e.getMessage()); }
        }});
    }

    private void reader(final Peer p, final boolean hostSide) {
        daemon("net-read-" + p.id, new Runnable() { public void run() {
            try {
                Reader r = new InputStreamReader(p.s.getInputStream(), "UTF-8");
                StringBuilder sb = new StringBuilder(); boolean skip = false; char[] buf = new char[4096]; int n;
                while ((n = r.read(buf)) > 0) {
                    for (int i = 0; i < n; i++) {
                        char c = buf[i];
                        if (c == '\n') { if (!skip && sb.length() > 0) l.onEvent("msg", p.id + "|" + sb); sb.setLength(0); skip = false; }
                        else if (!skip) { sb.append(c); if (sb.length() > MAX_LINE) { sb.setLength(0); skip = true; } }
                    }
                }
            } catch (IOException e) { /* соединение закрыто */ }
            p.close();
            if (hostSide) { peers.remove(p); if (hosting) l.onEvent("leave", String.valueOf(p.id)); }
            else if (clientOn) { clientOn = false; l.onEvent("disconnected", "1"); }
        }});
    }

    // ---------------------------------------------------------------- общее
    public void send(int to, String line) {
        if (line == null || line.indexOf('\n') >= 0 || line.length() > MAX_LINE) return;
        if (hosting) { for (Peer p : peers) if (to == 0 || p.id == to) p.send(line); }
        else { Peer u = upstream; if (u != null) u.send(line); }
    }

    public synchronized void stop() {
        hosting = false; clientOn = false;
        if (server != null) { try { server.close(); } catch (IOException e) { /* уже закрыт */ } server = null; }
        if (beaconSock != null) { beaconSock.close(); beaconSock = null; }
        for (Peer p : peers) p.close();
        peers.clear();
        Peer u = upstream; upstream = null; if (u != null) u.close();
    }

    public static String localIp() {
        String best = "";
        try {
            Enumeration<NetworkInterface> en = NetworkInterface.getNetworkInterfaces();
            while (en != null && en.hasMoreElements()) {
                NetworkInterface ni = en.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                Enumeration<InetAddress> as = ni.getInetAddresses();
                while (as.hasMoreElements()) {
                    InetAddress a = as.nextElement();
                    if (!(a instanceof Inet4Address) || !a.isSiteLocalAddress()) continue;
                    String name = ni.getName();
                    if (name.startsWith("wlan") || name.startsWith("ap") || name.startsWith("swlan")) return a.getHostAddress();
                    if (best.length() == 0) best = a.getHostAddress();
                }
            }
        } catch (Exception e) { /* нет сети */ }
        return best;
    }

    private static void daemon(String name, Runnable r) { Thread t = new Thread(r, name); t.setDaemon(true); t.start(); }
}
