CREATE INDEX transfers_destination_recent ON bank.transfers
 (destination_account,created_at DESC,transfer_id DESC);
ANALYZE bank.transfers;
