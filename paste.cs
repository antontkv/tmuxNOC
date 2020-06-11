// Taken from https://gist.github.com/jpflouret/19da43372e643352a1bf. Thank you.
// This program will output to stdout content of the system clipboard.
// Compile with Windows Command Line with this command:
// %SystemRoot%\Microsoft.NET\Framework\v3.5\csc /o paste.cs
// Make sure that paste.exe in the PATH.

using System;
using System.Windows.Forms;

namespace jpf {
    class paste {
        [STAThread]
        public static int Main(string[] args) {
            Console.Write(Clipboard.GetText());
            return 0;
        }
    }
}
