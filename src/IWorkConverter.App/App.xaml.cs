using System;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Markup;
using System.Windows.Threading;

namespace IWorkConverter.App
{
    public partial class App : Application
    {
        // App.xaml（テーマ）の読み込みは InitializeComponent の中で起きるため、
        // ハンドラーはコンストラクターで登録しておく必要がある
        public App()
        {
            DispatcherUnhandledException += OnDispatcherUnhandledException;
            AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandledException;
        }

        private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
        {
            Report(e.Exception);
            e.Handled = true;
        }

        private void OnDomainUnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            Report(e.ExceptionObject as Exception);
        }

        private static void Report(Exception ex)
        {
            if (ex == null) return;

            var sb = new StringBuilder();
            sb.AppendLine("iWorkConverter で処理されない例外が発生しました。");
            sb.AppendLine();

            var current = ex;
            int depth = 0;
            while (current != null && depth < 8)
            {
                sb.AppendLine("[" + depth + "] " + current.GetType().FullName);
                sb.AppendLine(current.Message);

                var xaml = current as XamlParseException;
                if (xaml != null)
                {
                    sb.AppendLine("XAML: " + (xaml.BaseUri == null ? "(不明)" : xaml.BaseUri.ToString()));
                    sb.AppendLine("行 " + xaml.LineNumber + " / 位置 " + xaml.LinePosition);
                }

                sb.AppendLine();
                current = current.InnerException;
                depth++;
            }

            sb.AppendLine("--- スタックトレース ---");
            sb.AppendLine(ex.ToString());

            string path = null;
            try
            {
                path = Path.Combine(Path.GetTempPath(), "iWorkConverter-error.txt");
                File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
            }
            catch { path = null; }

            string message = sb.ToString();
            if (message.Length > 2000) message = message.Substring(0, 2000) + Environment.NewLine + "…（以下省略）";
            if (path != null) message += Environment.NewLine + Environment.NewLine + "全文: " + path;

            MessageBox.Show(message, "iWorkConverter — エラー", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
