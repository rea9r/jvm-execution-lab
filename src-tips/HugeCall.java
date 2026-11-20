import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;

/** Calls f of the class named in args[0] 20,000 times per round and prints the time of each round in microseconds. */
public class HugeCall {
    public static void main(String[] args) throws Throwable {
        MethodHandle f = MethodHandles.lookup()
                .findStatic(Class.forName(args[0]), "f", MethodType.methodType(long.class, long.class));
        int rounds = Integer.parseInt(args[1]);
        long check = 0;
        StringBuilder out = new StringBuilder("round,elapsed_us\n");
        for (int r = 1; r <= rounds; r++) {
            long t0 = System.nanoTime();
            for (int i = 0; i < 20_000; i++) {
                check += (long) f.invokeExact((long) i);
            }
            out.append(r).append(',').append((System.nanoTime() - t0) / 1000).append('\n');
        }
        System.out.print(out);
        System.err.println("check=" + check);
    }
}
