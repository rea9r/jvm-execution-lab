public class TaxedCart {
    public interface TaxRule {
        long apply(long amount);
    }

    public static final class Standard implements TaxRule {
        public long apply(long amount) {
            return amount * 110 / 100;
        }
    }

    public static final class Reduced implements TaxRule {
        public long apply(long amount) {
            return amount * 108 / 100;
        }
    }

    public static final class Exempt implements TaxRule {
        public long apply(long amount) {
            return amount;
        }
    }

    public record Item(int price, int quantity, TaxRule rule) {}

    static long subtotal(Item item) {
        return (long) item.price() * item.quantity();
    }

    public static long total(Item[] items) {
        long sum = 0;
        for (Item item : items) {
            sum += item.rule().apply(subtotal(item));
        }
        return sum;
    }
}
