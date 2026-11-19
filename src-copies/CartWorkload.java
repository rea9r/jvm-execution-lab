import java.util.function.LongBinaryOperator;

public class CartWorkload implements LongBinaryOperator {
    public long applyAsLong(long rounds, long size) {
        Cart.Item[] items = new Cart.Item[(int) size];
        for (int i = 0; i < items.length; i++) {
            items[i] = new Cart.Item(100 + (i * 37) % 900, 1 + (i * 7) % 5);
        }
        long sum = 0;
        for (long r = 0; r < rounds; r++) {
            sum += Cart.total(items);
        }
        return sum;
    }
}
