public class Cart {
    public record Item(int price, int quantity) {}

    static long subtotal(Item item) {
        return (long) item.price() * item.quantity();
    }

    static long withTax(long amount) {
        return amount * 110 / 100;
    }

    public static long total(Item[] items) {
        long sum = 0;
        for (Item item : items) {
            sum += withTax(subtotal(item));
        }
        return sum;
    }
}
