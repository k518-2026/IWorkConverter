using System.Windows;
using IWorkConverter.App.ViewModels;

namespace IWorkConverter.App
{
    public partial class MainWindow : Window
    {
        private readonly MainViewModel _vm = new MainViewModel();

        public MainWindow()
        {
            InitializeComponent();
            DataContext = _vm;
        }

        private void Window_DragOver(object sender, DragEventArgs e)
        {
            bool ok = e.Data.GetDataPresent(DataFormats.FileDrop);
            e.Effects = ok ? DragDropEffects.Copy : DragDropEffects.None;
            _vm.IsDragOver = ok;
            e.Handled = true;
        }

        private void Window_DragLeave(object sender, DragEventArgs e)
        {
            _vm.IsDragOver = false;
        }

        private void Window_Drop(object sender, DragEventArgs e)
        {
            _vm.IsDragOver = false;
            if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;
            var paths = e.Data.GetData(DataFormats.FileDrop) as string[];
            if (paths != null) _vm.AddPaths(paths);
            e.Handled = true;
        }
    }
}
