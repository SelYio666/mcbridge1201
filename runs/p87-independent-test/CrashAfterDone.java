import java.io.*;
public class CrashAfterDone {
 public static void main(String[] args) throws Exception {
  System.out.println("Done (0.001s)! For help, type help");
  new BufferedReader(new InputStreamReader(System.in)).readLine();
  System.err.println("CONTROL: simulated post-boot JVM failure");
  System.exit(7);
 }
}
