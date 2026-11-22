package com.supertrader;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

@RestController
@RequestMapping("/api/paper")
public class PaperTradeController {
  private static final double INITIAL_CASH = 100000.0;
  private final Map<UUID, Trade> trades = new ConcurrentHashMap<>();

  public record OpenRequest(@NotBlank @Size(max=30) String symbol,
      @Positive double entryPrice, @Positive int quantity,
      @Positive double stopLoss, @Positive double target) {}
  public record Trade(UUID id, String symbol, double entryPrice, int quantity,
      double stopLoss, double target, String status, Instant openedAt,
      Double exitPrice, Double realizedPnl) {}
  public record CloseRequest(@Positive double exitPrice) {}

  @GetMapping("/trades")
  public Collection<Trade> list() { return trades.values(); }

  @PostMapping("/trades")
  @ResponseStatus(HttpStatus.CREATED)
  public Trade open(@Valid @RequestBody OpenRequest req) {
    if (req.stopLoss() >= req.entryPrice() || req.target() <= req.entryPrice())
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "For a long paper trade, stop loss must be below entry and target above entry.");
    double risk = (req.entryPrice() - req.stopLoss()) * req.quantity();
    if (risk > INITIAL_CASH * 0.01)
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Trade risk exceeds 1% of the ₹1,00,000 demo capital.");
    if (req.entryPrice() * req.quantity() > INITIAL_CASH)
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Insufficient demo capital.");
    Trade trade = new Trade(UUID.randomUUID(), req.symbol().toUpperCase(Locale.ROOT),
      req.entryPrice(), req.quantity(), req.stopLoss(), req.target(), "OPEN",
      Instant.now(), null, null);
    trades.put(trade.id(), trade);
    return trade;
  }

  @PostMapping("/trades/{id}/close")
  public Trade close(@PathVariable UUID id, @Valid @RequestBody CloseRequest req) {
    Trade old = trades.get(id);
    if (old == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Paper trade not found.");
    if (!old.status().equals("OPEN")) throw new ResponseStatusException(HttpStatus.CONFLICT, "Trade is already closed.");
    double pnl = (req.exitPrice() - old.entryPrice()) * old.quantity();
    Trade closed = new Trade(old.id(), old.symbol(), old.entryPrice(), old.quantity(),
      old.stopLoss(), old.target(), "CLOSED", old.openedAt(), req.exitPrice(), pnl);
    trades.put(id, closed);
    return closed;
  }

  @GetMapping("/summary")
  public Map<String,Object> summary() {
    double realized = trades.values().stream().filter(t -> t.realizedPnl() != null).mapToDouble(Trade::realizedPnl).sum();
    long open = trades.values().stream().filter(t -> t.status().equals("OPEN")).count();
    return Map.of("initialCapital", INITIAL_CASH, "realizedPnl", realized, "openTrades", open,
      "closedTrades", trades.size() - open, "mode", "PAPER_ONLY");
  }
}