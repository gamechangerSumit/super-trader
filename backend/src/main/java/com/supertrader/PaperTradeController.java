package com.supertrader;

import java.util.*;
import java.util.stream.Collectors;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;

@RestController
@RequestMapping("/api/paper")
public class PaperTradeController {
  private static final double INITIAL_CASH = 100000.0;
  private final PaperTradeRepository repository;

  public PaperTradeController(PaperTradeRepository repository) {
    this.repository = repository;
  }

  public record OpenRequest(
      @NotBlank @Size(max = 30) String symbol,
      @Positive double entryPrice,
      @Positive int quantity,
      @Positive double stopLoss,
      @Positive double target) {}

  public record CloseRequest(@Positive double exitPrice) {}

  @GetMapping("/trades")
  public List<PaperTrade> list() {
    return repository.findAll(Sort.by(Sort.Direction.DESC, "openedAt"));
  }

  @PostMapping("/trades")
  @ResponseStatus(HttpStatus.CREATED)
  public PaperTrade open(@Valid @RequestBody OpenRequest req) {
    String symbol = req.symbol().trim().toUpperCase(Locale.ROOT);
    if (req.stopLoss() >= req.entryPrice() || req.target() <= req.entryPrice()) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
          "For a long paper trade, stop loss must be below entry and target above entry.");
    }

    double risk = (req.entryPrice() - req.stopLoss()) * req.quantity();
    if (risk > INITIAL_CASH * 0.01) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
          "Trade risk exceeds 1% of the ₹1,00,000 demo capital.");
    }

    double requestedExposure = req.entryPrice() * req.quantity();
    double currentExposure = repository.findAll().stream()
        .filter(t -> "OPEN".equals(t.getStatus()))
        .mapToDouble(t -> t.getEntryPrice() * t.getQuantity())
        .sum();
    if (requestedExposure + currentExposure > INITIAL_CASH) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
          "Insufficient available demo capital.");
    }

    return repository.save(new PaperTrade(symbol, req.entryPrice(),
        req.quantity(), req.stopLoss(), req.target()));
  }

  @PostMapping("/trades/{id}/close")
  @Transactional
  public PaperTrade close(@PathVariable UUID id, @Valid @RequestBody CloseRequest req) {
    PaperTrade trade = repository.findById(id)
        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND,
            "Paper trade not found."));
    if (!"OPEN".equals(trade.getStatus())) {
      throw new ResponseStatusException(HttpStatus.CONFLICT, "Trade is already closed.");
    }
    trade.close(req.exitPrice());
    return repository.save(trade);
  }

  @GetMapping("/summary")
  public Map<String, Object> summary() {
    List<PaperTrade> all = repository.findAll();
    double realized = all.stream()
        .filter(t -> t.getRealizedPnl() != null)
        .mapToDouble(PaperTrade::getRealizedPnl)
        .sum();
    long open = all.stream().filter(t -> "OPEN".equals(t.getStatus())).count();
    double usedCapital = all.stream()
        .filter(t -> "OPEN".equals(t.getStatus()))
        .mapToDouble(t -> t.getEntryPrice() * t.getQuantity())
        .sum();
    return Map.of(
        "initialCapital", INITIAL_CASH,
        "availableCapital", INITIAL_CASH - usedCapital,
        "realizedPnl", realized,
        "openTrades", open,
        "closedTrades", all.size() - open,
        "mode", "PAPER_ONLY");
  }
}
