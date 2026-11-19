import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.LongBinaryOperator;

// Load Cart from a directory outside the class path once per class loader, so that each copy is a separate class
public class Copies {
    public static void main(String[] args) throws Exception {
        int copies = Integer.parseInt(args[0]);
        long rounds = Long.parseLong(args[1]);
        URL dir = Path.of(args[2]).toUri().toURL();

        phase("started");

        List<LongBinaryOperator> workloads = new ArrayList<>();
        long check = 0;
        for (int i = 0; i < copies; i++) {
            URLClassLoader loader = new URLClassLoader(new URL[] {dir}, ClassLoader.getPlatformClassLoader());
            LongBinaryOperator workload = (LongBinaryOperator) loader.loadClass("CartWorkload")
                    .getDeclaredConstructor()
                    .newInstance();
            check += workload.applyAsLong(1, 10);
            workloads.add(workload);
        }
        Thread.sleep(500);
        phase("loaded");

        for (LongBinaryOperator workload : workloads) {
            check += workload.applyAsLong(rounds, 1000);
        }
        Thread.sleep(500);
        phase("hot");

        for (int i = 1; i <= 3; i++) {
            System.gc();
            Thread.sleep(500);
            phase("after-gc" + i);
        }

        System.err.println("check=" + check);
    }

    // Wait for the driver to run jcmd against this process
    static void phase(String name) throws Exception {
        System.out.println("PHASE " + name + " " + ProcessHandle.current().pid());
        System.out.flush();
        while (System.in.read() != '\n') {
        }
    }
}
