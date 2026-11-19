public class CartOneMethod {
    public static long total(Cart.Item[] items) {
        long sum = 0;
        for (Cart.Item item : items) {
            sum += (long) item.price() * item.quantity() * 110 / 100;
        }
        return sum;
    }
}
