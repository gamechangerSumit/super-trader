package com.supertrader;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaperTradeRepository extends JpaRepository<PaperTrade, UUID> {
  long countByStatus(String status);
}
