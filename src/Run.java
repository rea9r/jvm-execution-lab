public class Run {
    public static void main(String[] args) {
        String variant = args[0];
        int rounds = Integer.parseInt(args[1]);
        int size = Integer.parseInt(args[2]);

        long[] starts = new long[rounds];
        long[] elapsed = new long[rounds];
        long check = 0;

        if (variant.equals("shift")) {
            // Only the standard rate during the first half, then all three rules
            TaxedCart.Item[] before = taxedItems(size, 1);
            TaxedCart.Item[] after = taxedItems(size, 3);
            for (int r = 0; r < rounds; r++) {
                TaxedCart.Item[] items = r < rounds / 2 ? before : after;
                long t0 = System.nanoTime();
                check += TaxedCart.total(items);
                long t1 = System.nanoTime();
                starts[r] = t0;
                elapsed[r] = t1 - t0;
            }
        } else if (variant.startsWith("taxed")) {
            int kinds = Integer.parseInt(variant.substring("taxed".length()));
            TaxedCart.Item[] items = taxedItems(size, kinds);
            for (int r = 0; r < rounds; r++) {
                long t0 = System.nanoTime();
                check += TaxedCart.total(items);
                long t1 = System.nanoTime();
                starts[r] = t0;
                elapsed[r] = t1 - t0;
            }
        } else {
            Cart.Item[] items = items(size);
            boolean oneMethod = variant.equals("onemethod");
            if (oneMethod) {
                for (int r = 0; r < rounds; r++) {
                    long t0 = System.nanoTime();
                    check += CartOneMethod.total(items);
                    long t1 = System.nanoTime();
                    starts[r] = t0;
                    elapsed[r] = t1 - t0;
                }
            } else {
                for (int r = 0; r < rounds; r++) {
                    long t0 = System.nanoTime();
                    check += Cart.total(items);
                    long t1 = System.nanoTime();
                    starts[r] = t0;
                    elapsed[r] = t1 - t0;
                }
            }
        }

        StringBuilder out = new StringBuilder("round,start_ns,elapsed_ns\n");
        for (int r = 0; r < rounds; r++) {
            out.append(r + 1).append(',').append(starts[r]).append(',').append(elapsed[r]).append('\n');
        }
        System.out.print(out);
        System.err.println("check=" + check);
    }

    static Cart.Item[] items(int size) {
        Cart.Item[] items = new Cart.Item[size];
        for (int i = 0; i < size; i++) {
            items[i] = new Cart.Item(100 + (i * 37) % 900, 1 + (i * 7) % 5);
        }
        return items;
    }

    static TaxedCart.Item[] taxedItems(int size, int kinds) {
        TaxedCart.TaxRule[] rules = {new TaxedCart.Standard(), new TaxedCart.Reduced(), new TaxedCart.Exempt()};
        TaxedCart.Item[] items = new TaxedCart.Item[size];
        int seed = 12345;
        for (int i = 0; i < size; i++) {
            seed = seed * 1103515245 + 12345;
            TaxedCart.TaxRule rule = rules[((seed >>> 16) & 0x7fff) % kinds];
            items[i] = new TaxedCart.Item(100 + (i * 37) % 900, 1 + (i * 7) % 5, rule);
        }
        return items;
    }
}
