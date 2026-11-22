package com.supertrader;

import java.time.Instant;
import java.util.UUID;
import jakarta.persistence.*;

@Entity
@Table(name = "paper_trades")
public class PaperTrade {
  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(nullable = false, length = 30)
  private String symbol;

  @Column(nullable = false)
  private double entryPrice;

  @Column(nullable = false)
  private int quantity;

  @Column(nullable = false)
  private double stopLoss;

  @Column(nullable = false)
  private double target;

  @Column(nullable = false, length = 12)
  private String status;

  @Column(nullable = false, updatable = false)
  private Instant openedAt;

  private Double exitPrice;
  private Double realizedPnl;

  protected PaperTrade() {}

  public PaperTrade(String symbol, double entryPrice, int quantity, double stopLoss, double target) {
    this.symbol = symbol;
    this.entryPrice = entryPrice;
    this.quantity = quantity;
    this.stopLoss = stopLoss;
    this.target = target;
    this.status = "OPEN";
    this.openedAt = Instant.now();
  }

  public void close(double price) {
    this.exitPrice = price;
    this.realizedPnl = (price - entryPrice) * quantity;
    this.status = "CLOSED";
  }

  public UUID getId() { return id; }
  public String getSymbol() { return symbol; }
  public double getEntryPrice() { return entryPrice; }
  public int getQuantity() { return quantity; }
  public double getStopLoss() { return stopLoss; }
  public double getTarget() { return target; }
  public String getStatus() { return status; }
  public Instant getOpenedAt() { return openedAt; }
  public Double getExitPrice() { return exitPrice; }
  public Double getRealizedPnl() { return realizedPnl; }
}
