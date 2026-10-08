using System;
using System.Windows;
using System.Windows.Media;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Wpf;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.IO;

namespace WpfHostPOC
{
    public class Program
    {
        [STAThread]
        public static void Main()
        {
            System.Windows.Application app = new System.Windows.Application();
            Window win = new Window();
            win.Title = "WPF Host POC";
            win.WindowStyle = WindowStyle.None;
            win.AllowsTransparency = true;
            win.Background = Brushes.Transparent;
            win.Topmost = true;
            win.ShowInTaskbar = false;
            win.Width = SystemParameters.PrimaryScreenWidth;
            win.Height = SystemParameters.PrimaryScreenHeight;
            win.Left = 0;
            win.Top = 0;

            WebView2 wv = new WebView2();
            wv.Width = win.Width;
            wv.Height = win.Height;
            wv.DefaultBackgroundColor = System.Drawing.Color.Transparent;
            win.Content = wv;

            string htmlPath = @"D:\Project\The-Great-Sage\overlay\great-sage-core.html";
            wv.Source = new Uri(htmlPath);

            // Fix: Move WebView2 initialization to the Loaded event to ensure the dispatcher is running.
            win.Loaded += async (s, e) => {
                try {
                    await wv.EnsureCoreWebView2Async();

                    wv.CoreWebView2.WebMessageReceived += (sender, args) => {
                        string message = args.TryGetWebMessageAsString();
                        if (message == null) return;

                        string traceMsg = $"[AUDIO_TRACE] WPF WebMessageReceived: {message}";
                        Console.WriteLine(traceMsg);
                        try { File.AppendAllText(@"D:\Project\The-Great-Sage\wpf_audio_trace.log", traceMsg + Environment.NewLine); } catch {}

                        if (message.StartsWith("AUDIO_ENDED:") || message.StartsWith("AUDIO_ERROR:")) {
                            SendEventToPython(message);
                        }
                    };
                    Console.WriteLine("[AUDIO_TRACE] WebView2 initialized. WPF Host is ready.");
                } catch (Exception ex) {
                    Console.WriteLine($"WebView2 initialization failed: {ex.Message}");
                }
            };

            Thread listenerThread = new Thread(() => {
                TcpListener server = new TcpListener(System.Net.IPAddress.Any, 9999);
                server.Start();
                while (true)
                {
                    try {
                        using (TcpClient client = server.AcceptTcpClient())
                        using (StreamReader reader = new StreamReader(client.GetStream()))
                        {
                            string script = reader.ReadLine();
                            if (script != null)
                            {
                                win.Dispatcher.Invoke(() => {
                                    try {
                                        wv.ExecuteScriptAsync(script);
                                    } catch (Exception ex) {
                                        Console.WriteLine("JS Error: " + ex.Message);
                                    }
                                });
                            }
                        }
                    } catch (Exception ex) {
                        Console.WriteLine("TCP Server Error: " + ex.Message);
                    }
                }
            });
            listenerThread.IsBackground = true;
            listenerThread.Start();

            win.Show();
            app.Run(win);
        }

        private static void SendEventToPython(string eventName)
        {
            try {
                string logPath = @"D:\Project\The-Great-Sage\wpf_audio_trace.log";
                string traceLine = $"[AUDIO_TRACE] WPF forwarding {eventName} to Python :9998";
                Console.WriteLine(traceLine);
                File.AppendAllText(logPath, traceLine + Environment.NewLine);

                using (TcpClient client = new TcpClient("127.0.0.1", 9998))
                {
                    string connectedLine = "[AUDIO_TRACE] WPF TCP connected";
                    Console.WriteLine(connectedLine);
                    File.AppendAllText(logPath, connectedLine + Environment.NewLine);

                    using (StreamWriter writer = new StreamWriter(client.GetStream()))
                    {
                        writer.WriteLine(eventName);
                        writer.Flush();
                        string sentLine = $"[AUDIO_TRACE] WPF TCP sent: {eventName}";
                        Console.WriteLine(sentLine);
                        File.AppendAllText(logPath, sentLine + Environment.NewLine);
                    }
                }
                string completedLine = "[AUDIO_TRACE] WPF SendEventToPython completed";
                Console.WriteLine(completedLine);
                File.AppendAllText(logPath, completedLine + Environment.NewLine);
            } catch (Exception ex) {
                string logPath = @"D:\Project\The-Great-Sage\wpf_audio_trace.log";
                string failLine = $"[AUDIO_TRACE] WPF TCP send failed: {ex.Message}";
                Console.WriteLine(failLine);
                File.AppendAllText(logPath, failLine + Environment.NewLine);
                Console.WriteLine("Error reporting event to Python: " + ex.Message);
            }
        }
    }
}