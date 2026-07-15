import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Card, Form, Input, Button, Result, Typography, Row, Col, Alert, Spin } from "antd";
import { CreditCardOutlined, SafetyCertificateOutlined, LockOutlined } from "@ant-design/icons";
import { PSS_API_URL } from "../services/api";


const { Title, Text } = Typography;

export const PaymentGatewayPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  
  // Extract parameters from URL
  const pnr = searchParams.get("pnr") || "";
  const amount = searchParams.get("amount") || "150";
  const flight = searchParams.get("flight") || "AA100";
  const origin = searchParams.get("origin") || "";
  const destination = searchParams.get("destination") || "";
  const date = searchParams.get("date") || "";

  // UI state
  const [cardNumber, setCardNumber] = useState("");
  const [cardName, setCardName] = useState("");
  const [cardExpiry, setCardExpiry] = useState("");
  const [loading, setLoading] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  // Determine card type logo/network name based on card number prefix
  const getCardType = (num: string) => {
    const cleanNum = num.replace(/\s+/g, "");
    if (cleanNum.startsWith("4")) return { name: "Visa", color: "#1a1f71" };
    if (cleanNum.startsWith("5")) return { name: "Mastercard", color: "#eb001b" };
    if (cleanNum.startsWith("3")) return { name: "American Express", color: "#007bc1" };
    if (cleanNum.startsWith("6")) return { name: "Discover", color: "#f26522" };
    return { name: "Unknown", color: "#64748b" };
  };

  const cardType = getCardType(cardNumber);

  // Format card number with spaces every 4 digits
  const handleCardNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "");
    const formatted = value.match(/.{1,4}/g)?.join(" ") || value;
    setCardNumber(formatted.slice(0, 19)); // Max 16 digits + 3 spaces
    form.setFieldsValue({ cardNumber: formatted.slice(0, 19) });
  };

  const handleExpiryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length > 2) {
      value = value.slice(0, 2) + "/" + value.slice(2, 4);
    }
    setCardExpiry(value.slice(0, 5));
    form.setFieldsValue({ expiry: value.slice(0, 5) });
  };

  const handlePayment = (values: any) => {
    const cleanCard = values.cardNumber.replace(/\s+/g, "");
    setLoading(true);
    setErrorMessage("");

    setTimeout(async () => {
      // 1. Mastercard network timeout
      if (cleanCard.startsWith("5100")) {
        setLoading(false);
        setPaymentStatus("error");
        setErrorMessage("Transaction Timeout: PSS payment gateway did not respond within 15 seconds. Please try again.");
        return;
      }

      // 2. American Express insufficient balance
      if (cleanCard.startsWith("3700")) {
        setLoading(false);
        setPaymentStatus("error");
        setErrorMessage("Payment Failed: Insufficient funds to clear transaction amount $" + amount + " on account.");
        return;
      }

      // 3. Discover decline
      if (cleanCard.startsWith("6011")) {
        setLoading(false);
        setPaymentStatus("error");
        setErrorMessage("Payment Declined: Transaction rejected by card issuing bank. (Response Code: 05 - DO NOT HONOR)");
        return;
      }

      // 4. Visa or fallback: Success
      if (cleanCard.startsWith("4") || cleanCard.length >= 15) {
        try {
          const res = await fetch(`${PSS_API_URL}/bookings/${pnr}/payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              amount: parseFloat(amount),
              payment_method: "card",
              idempotency_key: `${pnr}_${Date.now()}`
            })
          });

          if (res.ok) {
            if (window.opener) {
              window.opener.postMessage({ type: "PAYMENT_SUCCESS", pnr }, "*");
            }
            setLoading(false);
            setPaymentStatus("success");
          } else {
            const err = await res.json();
            setLoading(false);
            setPaymentStatus("error");
            setErrorMessage(err.detail || "Failed to process payment in Passenger Service System.");
          }
        } catch (e) {
          setLoading(false);
          setPaymentStatus("error");
          setErrorMessage("Failed to connect to PSS API server.");
        }
      } else {
        setLoading(false);
        setPaymentStatus("error");
        setErrorMessage("Invalid Card Number. Please enter a valid card prefix.");
      }
    }, 2000);
  };

  if (paymentStatus === "success") {
    return (
      <div style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        padding: "20px"
      }}>
        <Card style={{ maxWidth: 500, width: "100%", borderRadius: "16px", boxShadow: "0 10px 25px rgba(0,0,0,0.3)" }}>
          <Result
            status="success"
            title="Payment Completed Successfully!"
            subTitle={
              <div>
                <Text style={{ fontSize: "15px" }}>
                  Your ticket with PNR <strong>{pnr}</strong> has been updated to <strong>CONFIRMED (BOOKED)</strong>.
                </Text>
                <div style={{ marginTop: 12, padding: "8px 12px", background: "#f8fafc", borderRadius: 8 }}>
                  <strong>Flight:</strong> {flight} | <strong>Route:</strong> {origin} ➡️ {destination} | <strong>Date:</strong> {date}
                </div>
              </div>
            }
            extra={[
              <Alert 
                key="alert"
                message="Checkout Complete" 
                description="You may now close this browser tab and return to the AI Chatbot window. Your ticket will show as BOOKED in the Ticket Preview."
                type="success" 
                showIcon 
                style={{ textAlign: "left", marginBottom: 20 }}
              />,
              <Button type="primary" key="close" onClick={() => window.close()} style={{ width: "100%", height: "40px", borderRadius: "8px", background: "#10b981", border: "none" }}>
                Close Tab
              </Button>
            ]}
          />
        </Card>
      </div>
    );
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0b0f19 0%, #1e1b4b 100%)",
      padding: "20px",
      fontFamily: "system-ui, sans-serif"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px" }}>
        <span style={{ fontSize: "28px" }}>✈️</span>
        <Title level={3} style={{ color: "#fff", margin: 0, letterSpacing: "1px" }}>APEX AIRLINES CHECKOUT</Title>
      </div>

      <Row gutter={[24, 24]} style={{ maxWidth: 900, width: "100%" }}>
        {/* Left column: Summary & Card Mockup */}
        <Col xs={24} md={11}>
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Ticket Price Card */}
            <Card style={{
              background: "rgba(30, 41, 59, 0.5)",
              backdropFilter: "blur(8px)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "16px",
              color: "#fff"
            }}>
              <Title level={4} style={{ color: "#fff", margin: "0 0 16px 0" }}>Order Summary</Title>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <Text style={{ color: "#94a3b8" }}>Reservation PNR</Text>
                <Text style={{ color: "#fff", fontWeight: "bold", fontFamily: "monospace" }}>{pnr}</Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <Text style={{ color: "#94a3b8" }}>Flight Route</Text>
                <Text style={{ color: "#fff", fontWeight: "bold" }}>{origin} ➡️ {destination} ({flight})</Text>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <Text style={{ color: "#94a3b8" }}>Departure Date</Text>
                <Text style={{ color: "#fff" }}>{date}</Text>
              </div>
              <div style={{ height: "1px", background: "rgba(255,255,255,0.1)", margin: "16px 0" }} />
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <Text style={{ color: "#e2e8f0", fontSize: "16px" }}>Total Amount</Text>
                <Text style={{ color: "#34d399", fontSize: "28px", fontWeight: "800" }}>${amount}</Text>
              </div>
            </Card>

            {/* Virtual Credit Card Mockup */}
            <div style={{
              background: `linear-gradient(135deg, ${cardType.color} 0%, #0f172a 100%)`,
              borderRadius: "16px",
              padding: "24px",
              aspectRatio: "1.58",
              boxShadow: "0 15px 35px rgba(0,0,0,0.4)",
              border: "1px solid rgba(255,255,255,0.1)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              position: "relative",
              overflow: "hidden"
            }}>
              <div style={{
                position: "absolute",
                right: "-20px",
                bottom: "-20px",
                width: "120px",
                height: "120px",
                borderRadius: "50%",
                background: "rgba(255,255,255,0.05)"
              }} />
              
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ fontSize: "20px", color: "rgba(255,255,255,0.8)", fontWeight: "bold" }}>PAYMENT CARD</div>
                <div style={{ color: "#fff", fontWeight: "bold", fontSize: "18px" }}>{cardType.name}</div>
              </div>

              {/* Card Chip */}
              <div style={{
                width: "40px",
                height: "30px",
                background: "linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%)",
                borderRadius: "6px",
                margin: "12px 0"
              }} />

              {/* Card Number */}
              <div style={{
                color: "#fff",
                fontSize: "20px",
                fontFamily: "monospace",
                letterSpacing: "2px",
                textShadow: "1px 1px 2px rgba(0,0,0,0.5)"
              }}>
                {cardNumber || "•••• •••• •••• ••••"}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", marginTop: "12px" }}>
                <div>
                  <div style={{ fontSize: "9px", color: "rgba(255,255,255,0.5)" }}>CARDHOLDER NAME</div>
                  <div style={{ color: "#fff", fontSize: "14px", fontWeight: "500", textTransform: "uppercase" }}>
                    {cardName || "YOUR NAME HERE"}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "9px", color: "rgba(255,255,255,0.5)", textAlign: "right" }}>EXPIRES</div>
                  <div style={{ color: "#fff", fontSize: "14px", fontWeight: "500", textAlign: "right" }}>
                    {cardExpiry || "MM/YY"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Col>

        {/* Right column: Form details */}
        <Col xs={24} md={13}>
          <Card style={{
            background: "rgba(30, 41, 59, 0.4)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "16px",
            boxShadow: "0 8px 32px 0 rgba(0,0,0,0.2)"
          }}>
            <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "20px" }}>
              <LockOutlined style={{ color: "#10b981", fontSize: "18px" }} />
              <Title level={4} style={{ color: "#fff", margin: 0 }}>Secure Checkout</Title>
            </div>

            {errorMessage && (
              <Alert 
                message="Payment Unsuccessful" 
                description={errorMessage}
                type="error" 
                showIcon 
                style={{ marginBottom: 20, borderRadius: 8 }}
              />
            )}

            <Form
              form={form}
              layout="vertical"
              onFinish={handlePayment}
              requiredMark={false}
            >
              <Form.Item
                label={<span style={{ color: "#cbd5e1" }}>Cardholder Name</span>}
                name="cardholderName"
                rules={[{ required: true, message: "Please enter your name" }]}
              >
                <Input 
                  placeholder="e.g. Alex Mercer" 
                  value={cardName} 
                  onChange={(e) => {
                    setCardName(e.target.value);
                    form.setFieldsValue({ cardholderName: e.target.value });
                  }}
                  style={{ background: "rgba(15, 23, 42, 0.6)", color: "#fff", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", height: "40px" }}
                />
              </Form.Item>

              <Form.Item
                label={<span style={{ color: "#cbd5e1" }}>Card Number</span>}
                name="cardNumber"
                rules={[{ required: true, message: "Please enter your card number" }]}
              >
                <Input 
                  placeholder="4000 1234 5678 9010" 
                  prefix={<CreditCardOutlined style={{ color: "rgba(255,255,255,0.4)" }} />}
                  onChange={handleCardNumberChange}
                  style={{ background: "rgba(15, 23, 42, 0.6)", color: "#fff", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", height: "40px" }}
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    label={<span style={{ color: "#cbd5e1" }}>Expiration Date</span>}
                    name="expiry"
                    rules={[{ required: true, message: "Required" }]}
                  >
                    <Input 
                      placeholder="MM/YY" 
                      onChange={handleExpiryChange}
                      style={{ background: "rgba(15, 23, 42, 0.6)", color: "#fff", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", height: "40px" }}
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    label={<span style={{ color: "#cbd5e1" }}>CVV</span>}
                    name="cvv"
                    rules={[{ required: true, message: "Required" }]}
                  >
                    <Input.Password 
                      placeholder="e.g. 123" 
                      maxLength={4}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, "");
                        form.setFieldsValue({ cvv: val });
                      }}
                      style={{ background: "rgba(15, 23, 42, 0.6)", color: "#fff", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", height: "40px" }}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <div style={{ marginTop: "12px", background: "rgba(15, 23, 42, 0.3)", padding: "12px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.05)", marginBottom: "20px" }}>
                <Text style={{ color: "#94a3b8", fontSize: "12px", display: "block" }}>
                  💡 <strong>Simulator Card Patterns:</strong>
                </Text>
                <ul style={{ color: "#94a3b8", fontSize: "11px", margin: "4px 0 0 16px", padding: 0 }}>
                  <li>Visa (prefix <strong style={{ color: "#fff" }}>4</strong>): Success</li>
                  <li>Mastercard (prefix <strong style={{ color: "#fff" }}>5100</strong>): Network Timeout simulation</li>
                  <li>Amex (prefix <strong style={{ color: "#fff" }}>3700</strong>): Insufficient Balance simulation</li>
                  <li>Discover (prefix <strong style={{ color: "#fff" }}>6011</strong>): Fails / Card Declined simulation</li>
                </ul>
              </div>

              <Form.Item style={{ marginBottom: 0 }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  icon={<SafetyCertificateOutlined />}
                  style={{ 
                    width: "100%", 
                    height: "46px", 
                    borderRadius: "8px", 
                    fontSize: "15px", 
                    fontWeight: "bold",
                    background: "linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%)",
                    border: "none",
                    boxShadow: "0 4px 10px rgba(59, 130, 246, 0.4)"
                  }}
                >
                  {loading ? <Spin size="small" style={{ marginRight: 8 }} /> : null}
                  Authorize Payment of ${amount}
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};
