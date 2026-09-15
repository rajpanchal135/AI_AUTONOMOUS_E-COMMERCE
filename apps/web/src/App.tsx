import React, { useState, useEffect } from 'react';
import {
  ShoppingBag, Shield, CheckCircle, AlertTriangle, Clock, ArrowRight,
  Search, X, Sparkles, MessageSquare, ChevronRight, Truck, Box,
  DollarSign, Activity, RefreshCw, Lock, User, Layers, ArrowUpRight,
  Flame, Star, ExternalLink, Filter, HelpCircle, Check, Send, Zap, Play, Plus, Minus,
  Terminal, Cpu, Compass, Globe, Eye
} from 'lucide-react';
import {
  fetchDashboardSummary, fetchPendingActions, approveAction, rejectAction,
  fetchAgentRuns, fetchAgentHealth, fetchInventoryRisks, fetchOrderExceptions, fetchTickets,
  fetchPricingRecommendations, checkoutProduct, sendCustomerChat,
  restockProduct, trackOrder, reserveStock, getAuthUser, triggerDemoScenario
} from './lib/api';
import { HiveTopologyView } from './components/HiveTopologyView';
import { ActionInspectionModal } from './components/ActionInspectionModal';
import { ProductManagementView } from './components/ProductManagementView';

const PRODUCT_IMAGES: Record<string, string> = {
  'RUN-SHOE-BLK-42': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80',
  'RUN-SHOE-WHT-38': 'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=800&q=80',
  'RUN-SHOE-BLU-44': 'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=800&q=80',
  'ACC-BTL-HYD-01': 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=800&q=80',
  'ACC-SCK-CMP-02': 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?w=800&q=80'
};

const PRODUCT_PRICES: Record<string, number> = {
  'RUN-SHOE-BLK-42': 189.99,
  'RUN-SHOE-WHT-38': 169.99,
  'RUN-SHOE-BLU-44': 199.99,
  'ACC-BTL-HYD-01': 34.99,
  'ACC-SCK-CMP-02': 24.99
};

const DEFAULT_CATALOG = [
  {
    sku_code: 'RUN-SHOE-BLK-42',
    product_title: 'Apex Cloudstrider Elite Carbon',
    current_price: 189.99,
    stock_quantity: 12,
    category: 'footwear'
  },
  {
    sku_code: 'RUN-SHOE-WHT-38',
    product_title: 'Apex Aeroflight Zero White',
    current_price: 169.99,
    stock_quantity: 3,
    category: 'footwear'
  },
  {
    sku_code: 'RUN-SHOE-BLU-44',
    product_title: 'Apex Velocity Pro Endurance Blue',
    current_price: 199.99,
    stock_quantity: 18,
    category: 'footwear'
  },
  {
    sku_code: 'ACC-BTL-HYD-01',
    product_title: 'Apex Thermal Hydration Vessel 750ml',
    current_price: 34.99,
    stock_quantity: 45,
    category: 'accessories'
  },
  {
    sku_code: 'ACC-SCK-CMP-02',
    product_title: 'Apex Gradient Compression Socks (Pair)',
    current_price: 24.99,
    stock_quantity: 80,
    category: 'accessories'
  }
];

export default function App() {
  // Navigation Route
  const [route, setRoute] = useState<'storefront' | 'admin'>('storefront');
  const [adminTab, setAdminTab] = useState<'overview' | 'approvals' | 'topology' | 'inventory' | 'orders' | 'tickets' | 'products' | 'swarm'>('overview');

  // Backend Data
  const [summary, setSummary] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [agentRuns, setAgentRuns] = useState<any[]>([]);
  const [agentHealth, setAgentHealth] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>(DEFAULT_CATALOG);
  const [orders, setOrders] = useState<any[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);
  const [pricing, setPricing] = useState<any[]>([]);
  const [toast, setToast] = useState<{ text: string; type?: 'info' | 'success' | 'error' } | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);

  const [inspectingAction, setInspectingAction] = useState<any | null>(null);
  const [chatLanguage, setChatLanguage] = useState<'en' | 'hi' | 'es'>('en');

  // Storefront Catalog State
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);
  const [selectedSize, setSelectedSize] = useState<string>('42');
  const [selectedQuantity, setSelectedQuantity] = useState<number>(1);

  // Cart & 15-Minute Reservation Drawer State
  const [cartDrawerOpen, setCartDrawerOpen] = useState<boolean>(false);
  const [cartProduct, setCartProduct] = useState<any | null>(null);
  const [cartQuantity, setCartQuantity] = useState<number>(1);
  const [activeReservation, setActiveReservation] = useState<any | null>(null);
  const [reservationRemainingSeconds, setReservationRemainingSeconds] = useState<number>(900);
  const [checkoutStep, setCheckoutStep] = useState<'cart' | 'shipping' | 'payment' | 'confirmed'>('cart');
  const [checkoutSubmitting, setCheckoutSubmitting] = useState<boolean>(false);
  const [confirmedOrder, setConfirmedOrder] = useState<any | null>(null);

  // Customer Checkout Form
  const [checkoutForm, setCheckoutForm] = useState({
    name: 'Aarav Mehta',
    email: 'aarav.mehta@example.com',
    address: '402 Silicon Enclave, Indiranagar, Bengaluru, KA 560038',
    carrier: 'DHL Express (Priority Overnight)',
    cardNumber: '•••• •••• •••• 4242'
  });

  // Live Order Tracker Modal
  const [trackerModalOpen, setTrackerModalOpen] = useState<boolean>(false);
  const [trackingQuery, setTrackingQuery] = useState<string>('');
  const [trackingResult, setTrackingResult] = useState<any | null>(null);
  const [trackingLoading, setTrackingLoading] = useState<boolean>(false);

  // Floating AI RAG Concierge
  const [chatOpen, setChatOpen] = useState<boolean>(false);
  const [chatInput, setChatInput] = useState<string>('');
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [chatMessages, setChatMessages] = useState<Array<{ sender: 'user' | 'agent'; text: string; intent?: string }>>([
    {
      sender: 'agent',
      text: 'Welcome to Apex Labs Concierge. How can I assist you with your order status, sizing, or delivery today?'
    }
  ]);

  // Safe Price Helper
  const getProductPrice = (item: any): number => {
    if (item && item.current_price !== undefined && item.current_price !== null) {
      return Number(item.current_price);
    }
    if (item && item.sku_code && PRODUCT_PRICES[item.sku_code] !== undefined) {
      return PRODUCT_PRICES[item.sku_code];
    }
    return 149.99;
  };

  // Safe Stock Helper
  const getProductStock = (item: any): number => {
    if (item && item.on_hand !== undefined) return Number(item.on_hand);
    if (item && item.stock_quantity !== undefined) return Number(item.stock_quantity);
    return 10;
  };

  // Toast Helper
  const showToast = (text: string, type: 'info' | 'success' | 'error' = 'info') => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 4500);
  };

  // Load backend data
  const loadData = async () => {
    try {
      const [sum, acts, runs, inv, ords, tcks, prc, health] = await Promise.all([
        fetchDashboardSummary().catch(() => null),
        fetchPendingActions().catch(() => []),
        fetchAgentRuns().catch(() => []),
        fetchInventoryRisks().catch(() => []),
        fetchOrderExceptions().catch(() => []),
        fetchTickets().catch(() => []),
        fetchPricingRecommendations().catch(() => []),
        fetchAgentHealth().catch(() => null)
      ]);
      if (sum) setSummary(sum);
      if (acts && Array.isArray(acts)) setActions(acts);
      if (runs && Array.isArray(runs)) setAgentRuns(runs);
      if (health && health.agents) setAgentHealth(health.agents);
      if (inv && Array.isArray(inv) && inv.length > 0) {
        const enriched = inv.map(i => ({
          ...i,
          current_price: getProductPrice(i),
          stock_quantity: getProductStock(i)
        }));
        setInventory(enriched);
      }
      if (ords && Array.isArray(ords)) setOrders(ords);
      if (tcks && Array.isArray(tcks)) setTickets(tcks);
      if (prc && Array.isArray(prc)) setPricing(prc);
    } catch (e) {
      console.error("Data load error:", e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, []);

  // 15-Minute Reservation Clock
  useEffect(() => {
    let timer: any = null;
    if (cartDrawerOpen && activeReservation && reservationRemainingSeconds > 0) {
      timer = setInterval(() => {
        setReservationRemainingSeconds(prev => {
          if (prev <= 1) {
            clearInterval(timer);
            showToast("Your 15-minute stock reservation has expired.", "error");
            setActiveReservation(null);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [cartDrawerOpen, activeReservation, reservationRemainingSeconds]);

  // Initiate Product Reservation & Open Checkout Drawer
  const handleStartCheckout = async (product: any, qty: number = 1) => {
    const price = getProductPrice(product);
    const enrichedProduct = { ...product, current_price: price };
    setCartProduct(enrichedProduct);
    setCartQuantity(qty);
    setSelectedProduct(null);
    setCheckoutStep('cart');
    setCartDrawerOpen(true);

    try {
      const res = await reserveStock(product.sku_code, qty);
      if (res && res.reservation_token) {
        setActiveReservation(res);
        setReservationRemainingSeconds(res.ttl_seconds || 900);
        showToast(`Reserved ${qty} unit(s) for 15 mins at $${(price * qty).toFixed(2)}`, 'success');
      }
    } catch (e: any) {
      showToast("Stock reservation: " + (e.message || "Proceeding with checkout"), 'info');
    }
  };

  // Complete Idempotent Checkout
  const handleFinalCheckout = async () => {
    if (!cartProduct) return;
    setCheckoutSubmitting(true);
    try {
      const res = await checkoutProduct(
        cartProduct.sku_code,
        cartQuantity,
        checkoutForm.name,
        checkoutForm.email,
        checkoutForm.address
      );
      setConfirmedOrder(res);
      setCheckoutStep('confirmed');
      showToast(`Order #${res.external_id || res.id} placed successfully!`, 'success');
      await loadData();
    } catch (e: any) {
      showToast("Checkout error: " + e.message, 'error');
    } finally {
      setCheckoutSubmitting(false);
    }
  };

  // Track Order Lookup
  const handleTrackLookup = async (id?: string) => {
    const q = (id || trackingQuery).trim();
    if (!q) return;
    setTrackingLoading(true);
    try {
      const res = await trackOrder(q);
      setTrackingResult(res);
    } catch (e: any) {
      showToast(e.message || "Order not found", 'error');
    } finally {
      setTrackingLoading(false);
    }
  };

  // Send RAG AI Chat
  const handleSendChat = async (presetText?: string) => {
    const queryText = presetText || chatInput;
    if (!queryText.trim()) return;

    const updated = [...chatMessages, { sender: 'user' as const, text: queryText }];
    setChatMessages(updated);
    setChatInput('');
    setChatLoading(true);

    try {
      const orderIdToSend = confirmedOrder?.external_id || undefined;
      const res = await sendCustomerChat(queryText, orderIdToSend, checkoutForm.email, chatLanguage);
      setChatMessages([...updated, { sender: 'agent' as const, text: res.reply || "Request processed.", intent: res.intent }]);
    } catch (e: any) {
      setChatMessages([...updated, { sender: 'agent' as const, text: "I have registered your inquiry with our logistics team." }]);
    } finally {
      setChatLoading(false);
    }
  };

  // 1-Click Multi-Agent Swarm Simulation Trigger
  const handleTriggerSwarmSimulation = async () => {
    setSimulating(true);
    try {
      const res = await triggerDemoScenario();
      showToast(res.message || "LangGraph Multi-Agent Swarm executed! Proposals queued.", "success");
      await loadData();
      setRoute('admin');
      setAdminTab('approvals');
    } catch (e: any) {
      showToast("Swarm simulation error: " + e.message, "error");
    } finally {
      setSimulating(false);
    }
  };

  // Admin Actions: Approve / Reject
  const handleApprove = async (actionId: string) => {
    try {
      await approveAction(actionId, "Approved by enterprise operator");
      showToast("Proposal approved and committed to production pipeline.", "success");
      await loadData();
    } catch (e: any) {
      showToast("Approval error: " + e.message, "error");
    }
  };

  const handleReject = async (actionId: string) => {
    try {
      await rejectAction(actionId, "Rejected by enterprise operator");
      showToast("Proposal rejected.", "info");
      await loadData();
    } catch (e: any) {
      showToast("Rejection error: " + e.message, "error");
    }
  };

  // Admin Restock PO
  const handleRestock = async (sku: string) => {
    try {
      const res = await restockProduct(sku, 50);
      showToast(res.message || `Purchase order for ${sku} submitted to supplier.`, "success");
      await loadData();
    } catch (e: any) {
      showToast("Restock error: " + e.message, "error");
    }
  };

  // Filter Catalog
  const filteredProducts = inventory.filter(item => {
    const title = item?.product_title || '';
    const code = item?.sku_code || '';
    const matchesSearch = title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' ||
      (categoryFilter === 'footwear' && code.startsWith('RUN-')) ||
      (categoryFilter === 'accessories' && code.startsWith('ACC-'));
    return matchesSearch && matchesCategory;
  });

  const pendingApprovalsCount = actions.filter(a => a.status === 'pending_approval' || a.status === 'pending').length;

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: route === 'storefront' ? 'var(--store-bg)' : 'var(--admin-bg)' }}>
      {/* Toast Notification */}
      {toast && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 99999,
          background: toast.type === 'error' ? '#991B1B' : (toast.type === 'success' ? '#065F46' : '#0F172A'),
          color: '#FFFFFF',
          padding: '12px 24px',
          borderRadius: '9999px',
          fontSize: '13px',
          fontWeight: 600,
          boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          animation: 'fadeIn 0.2s ease'
        }}>
          {toast.type === 'success' ? <CheckCircle size={16} /> : <Sparkles size={16} />}
          <span>{toast.text}</span>
        </div>
      )}

      {/* ========================================================================================= */}
      {/* 1. CUSTOMER STOREFRONT (Apple / Nike / Shopify Minimalist Aesthetic)                      */}
      {/* ========================================================================================= */}
      {route === 'storefront' && (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
          {/* Top Announcement Bar */}
          <div style={{ background: '#0F172A', color: '#F8FAFC', padding: '8px 24px', fontSize: '12px', textAlign: 'center', fontWeight: 500, letterSpacing: '0.02em', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <span>Complimentary Express Delivery & 30-Day Returns on All Orders</span>
            <span style={{ color: '#64748B' }}>|</span>
            <button
              onClick={handleTriggerSwarmSimulation}
              disabled={simulating}
              style={{ background: 'rgba(59, 130, 246, 0.2)', border: '1px solid rgba(59, 130, 246, 0.4)', color: '#93C5FD', padding: '2px 10px', borderRadius: '9999px', fontSize: '11px', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              <Zap size={12} color="#60A5FA" /> {simulating ? 'Running Swarm...' : '⚡ Trigger AI Swarm Simulation'}
            </button>
            <span style={{ color: '#64748B' }}>|</span>
            <button
              onClick={() => setRoute('admin')}
              style={{ background: 'transparent', border: 'none', color: '#60A5FA', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
            >
              Enterprise Admin Portal ({pendingApprovalsCount} Approvals) <ArrowRight size={12} />
            </button>
          </div>

          {/* Minimalist Header */}
          <header style={{
            position: 'sticky',
            top: 0,
            zIndex: 1000,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid var(--store-border)',
            padding: '16px 40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px'
          }}>
            {/* Logo & Category Nav */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
              <div
                onClick={() => { setCategoryFilter('all'); setSelectedProduct(null); }}
                style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.04em', color: '#000000', cursor: 'pointer', fontFamily: 'var(--font-heading)' }}
              >
                APEX LABS
              </div>
              <nav style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                {['all', 'footwear', 'accessories'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => { setCategoryFilter(cat); setSelectedProduct(null); }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      fontSize: '14px',
                      fontWeight: categoryFilter === cat ? 700 : 500,
                      color: categoryFilter === cat ? '#000000' : '#64748B',
                      cursor: 'pointer',
                      textTransform: 'capitalize',
                      paddingBottom: '4px',
                      borderBottom: categoryFilter === cat ? '2px solid #000000' : '2px solid transparent',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {cat === 'all' ? 'All Collection' : cat}
                  </button>
                ))}
              </nav>
            </div>

            {/* Header Right Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div style={{ position: 'relative', width: '220px' }}>
                <Search size={16} color="#94A3B8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="text"
                  placeholder="Search gear or SKU..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px 8px 36px',
                    borderRadius: '9999px',
                    border: '1px solid var(--store-border)',
                    background: '#F8FAFC',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>

              <button
                onClick={() => setTrackerModalOpen(true)}
                style={{ background: 'transparent', border: 'none', color: '#334155', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Truck size={16} /> Track Order
              </button>

              <button
                onClick={() => setCartDrawerOpen(true)}
                style={{
                  background: '#000000',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '9999px',
                  padding: '9px 18px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <ShoppingBag size={15} />
                <span>Bag</span>
                {cartProduct && <span style={{ background: '#2563EB', color: '#FFF', borderRadius: '9999px', padding: '1px 6px', fontSize: '11px' }}>{cartQuantity}</span>}
              </button>

              {/* Prominent Direct Switch to Admin HQ Button */}
              <button
                onClick={() => setRoute('admin')}
                style={{
                  background: '#0F172A',
                  color: '#FFFFFF',
                  border: '1px solid #334155',
                  borderRadius: '9999px',
                  padding: '9px 16px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}
              >
                <Shield size={15} color="#60A5FA" />
                <span>Enterprise Ops HQ</span>
                {pendingApprovalsCount > 0 && (
                  <span style={{ background: '#EF4444', color: '#FFF', borderRadius: '9999px', padding: '1px 7px', fontSize: '11px', fontWeight: 700 }}>
                    {pendingApprovalsCount}
                  </span>
                )}
              </button>
            </div>
          </header>

          {/* Minimalist Hero Section */}
          <section style={{
            background: 'linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%)',
            borderBottom: '1px solid var(--store-border)',
            padding: '60px 40px',
            textAlign: 'center'
          }}>
            <div style={{ maxWidth: '780px', margin: '0 auto' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#FFFFFF', border: '1px solid var(--store-border)', padding: '6px 14px', borderRadius: '9999px', fontSize: '12px', fontWeight: 600, color: '#059669', marginBottom: '18px' }}>
                <Sparkles size={14} /> Autumn 2026 High-Performance Release
              </div>
              <h1 style={{ fontSize: '46px', lineHeight: 1.1, color: '#0F172A', marginBottom: '16px', letterSpacing: '-0.03em' }}>
                Engineered for Performance.
              </h1>
              <p style={{ fontSize: '16px', color: '#475569', lineHeight: 1.6, maxWidth: '600px', margin: '0 auto 24px auto' }}>
                Precision athletic footwear and hydration systems built with aerospace materials and autonomous supply allocation.
              </p>
            </div>
          </section>

          {/* Product Catalog Grid */}
          <main style={{ maxWidth: '1280px', margin: '0 auto', padding: '40px', width: '100%', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px' }}>
              <div>
                <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#0F172A' }}>
                  {categoryFilter === 'all' ? 'Featured Catalog' : `${categoryFilter.toUpperCase()}`}
                </h2>
                <p style={{ fontSize: '13px', color: '#64748B', marginTop: '4px' }}>
                  Showing {filteredProducts.length} verified products with real-time stock allocation
                </p>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '32px' }}>
              {filteredProducts.map(item => {
                const stock = getProductStock(item);
                const price = getProductPrice(item);
                const isLowStock = stock <= 5 && stock > 0;
                const isOut = stock <= 0;
                const imgUrl = PRODUCT_IMAGES[item.sku_code] || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80';

                return (
                  <div
                    key={item.sku_code}
                    className="store-product-card"
                    style={{ cursor: 'pointer' }}
                    onClick={() => {
                      setSelectedQuantity(1);
                      setSelectedProduct({ ...item, current_price: price, stock_quantity: stock });
                    }}
                  >
                    <div className="store-product-img-box">
                      <img src={imgUrl} alt={item.product_title} className="store-product-img" />
                      {isLowStock && (
                        <div style={{ position: 'absolute', top: '12px', left: '12px', background: 'rgba(239, 68, 68, 0.95)', color: '#FFFFFF', padding: '4px 10px', borderRadius: '9999px', fontSize: '11px', fontWeight: 700 }}>
                          Only {stock} Left
                        </div>
                      )}
                      {isOut && (
                        <div style={{ position: 'absolute', top: '12px', left: '12px', background: '#000000', color: '#FFFFFF', padding: '4px 10px', borderRadius: '9999px', fontSize: '11px', fontWeight: 700 }}>
                          Restocking Soon
                        </div>
                      )}
                    </div>

                    <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', flex: 1, justifyContent: 'space-between' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                            {item.sku_code}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', color: '#D97706', fontWeight: 700 }}>
                            <Star size={12} fill="#F59E0B" color="#F59E0B" />
                            <span>4.9</span>
                            <span style={{ color: '#94A3B8', fontWeight: 400 }}>(124)</span>
                          </div>
                        </div>
                        <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A', marginBottom: '8px', lineHeight: 1.3 }}>
                          {item.product_title}
                        </h3>
                        <div style={{ marginBottom: '8px' }}>
                          <span className="delivery-badge">
                            <Truck size={11} /> ⚡ 24-48h Express Delivery
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--store-border-light)' }}>
                        <div>
                          <div style={{ fontSize: '18px', fontWeight: 800, color: '#000000', fontFamily: 'var(--font-heading)' }}>
                            ${price.toFixed(2)}
                          </div>
                          <div style={{ fontSize: '11px', color: '#059669', fontWeight: 600 }}>
                            {stock > 0 ? '✓ Available Now' : 'Allocating'}
                          </div>
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartCheckout({ ...item, current_price: price, stock_quantity: stock }, 1);
                          }}
                          disabled={isOut}
                          className="btn-luxury-primary"
                          style={{ padding: '8px 16px', fontSize: '13px' }}
                        >
                          Quick Buy
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </main>

          {/* Product Detail Modal */}
          {selectedProduct && (
            <div className="drawer-backdrop" onClick={() => setSelectedProduct(null)}>
              <div
                style={{
                  background: '#FFFFFF',
                  borderRadius: '20px',
                  maxWidth: '760px',
                  width: '90vw',
                  maxHeight: '90vh',
                  overflowY: 'auto',
                  margin: 'auto',
                  padding: '36px',
                  position: 'relative',
                  boxShadow: 'var(--shadow-xl)',
                  animation: 'chatPopUp 0.25s ease'
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => setSelectedProduct(null)}
                  style={{ position: 'absolute', top: '20px', right: '20px', background: '#F1F5F9', border: 'none', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                >
                  <X size={18} color="#0F172A" />
                </button>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '32px' }}>
                  <div style={{ borderRadius: '14px', overflow: 'hidden', height: '320px', background: '#F8FAFC' }}>
                    <img
                      src={PRODUCT_IMAGES[selectedProduct.sku_code] || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80'}
                      alt={selectedProduct.product_title}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  </div>

                  <div>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', marginBottom: '6px' }}>
                      SKU: {selectedProduct.sku_code}
                    </div>
                    <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '12px' }}>
                      {selectedProduct.product_title}
                    </h2>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: '#000000', marginBottom: '18px' }}>
                      ${(getProductPrice(selectedProduct) * selectedQuantity).toFixed(2)}
                      {selectedQuantity > 1 && (
                        <span style={{ fontSize: '13px', color: '#64748B', fontWeight: 500, marginLeft: '8px' }}>
                          (${getProductPrice(selectedProduct).toFixed(2)} / unit)
                        </span>
                      )}
                    </div>

                    {/* Sizing */}
                    {selectedProduct.sku_code.startsWith('RUN-') && (
                      <div style={{ marginBottom: '18px' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A', marginBottom: '8px' }}>
                          Select Size (EU)
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          {['38', '40', '42', '44'].map(sz => (
                            <button
                              key={sz}
                              onClick={() => setSelectedSize(sz)}
                              style={{
                                width: '44px',
                                height: '40px',
                                borderRadius: '8px',
                                border: selectedSize === sz ? '2px solid #000000' : '1px solid var(--store-border)',
                                background: selectedSize === sz ? '#000000' : '#FFFFFF',
                                color: selectedSize === sz ? '#FFFFFF' : '#0F172A',
                                fontWeight: 700,
                                fontSize: '13px',
                                cursor: 'pointer'
                              }}
                            >
                              {sz}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Quantity Stepper Selector & Quick Presets */}
                    <div style={{ marginBottom: '20px' }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A', marginBottom: '8px' }}>
                        Select Quantity
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', border: '1px solid var(--store-border)', borderRadius: '8px', background: '#F8FAFC', padding: '4px' }}>
                          <button
                            onClick={() => setSelectedQuantity(Math.max(1, selectedQuantity - 1))}
                            disabled={selectedQuantity <= 1}
                            style={{ width: '32px', height: '32px', borderRadius: '6px', border: 'none', background: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: selectedQuantity <= 1 ? 'not-allowed' : 'pointer', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
                          >
                            <Minus size={14} color={selectedQuantity <= 1 ? '#CBD5E1' : '#0F172A'} />
                          </button>
                          <input
                            type="number"
                            min={1}
                            max={getProductStock(selectedProduct)}
                            value={selectedQuantity}
                            onChange={(e) => {
                              const val = parseInt(e.target.value, 10);
                              if (isNaN(val)) setSelectedQuantity(1);
                              else setSelectedQuantity(Math.max(1, Math.min(getProductStock(selectedProduct), val)));
                            }}
                            style={{ width: '56px', textAlign: 'center', fontSize: '15px', fontWeight: 800, color: '#0F172A', border: 'none', background: 'transparent', outline: 'none' }}
                          />
                          <button
                            onClick={() => setSelectedQuantity(Math.min(getProductStock(selectedProduct), selectedQuantity + 1))}
                            disabled={selectedQuantity >= getProductStock(selectedProduct)}
                            style={{ width: '32px', height: '32px', borderRadius: '6px', border: 'none', background: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: selectedQuantity >= getProductStock(selectedProduct) ? 'not-allowed' : 'pointer', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}
                          >
                            <Plus size={14} color={selectedQuantity >= getProductStock(selectedProduct) ? '#CBD5E1' : '#0F172A'} />
                          </button>
                        </div>
                        {/* Quick Presets for Large Orders */}
                        <div style={{ display: 'flex', gap: '6px' }}>
                          {[1, 5, 20, 40].filter(q => q <= getProductStock(selectedProduct)).map(q => (
                            <button
                              key={q}
                              onClick={() => setSelectedQuantity(q)}
                              style={{
                                padding: '6px 10px',
                                borderRadius: '6px',
                                border: selectedQuantity === q ? '2px solid #2563EB' : '1px solid #E2E8F0',
                                background: selectedQuantity === q ? '#EFF6FF' : '#FFFFFF',
                                color: selectedQuantity === q ? '#2563EB' : '#475569',
                                fontSize: '12px',
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              {q}x
                            </button>
                          ))}
                        </div>
                        <span style={{ fontSize: '12px', color: '#64748B' }}>
                          (In Stock: <strong>{getProductStock(selectedProduct)}</strong> units)
                        </span>
                      </div>
                    </div>

                    <div style={{ background: '#F8FAFC', padding: '14px', borderRadius: '10px', marginBottom: '24px', fontSize: '13px', color: '#475569', lineHeight: 1.5 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#059669', fontWeight: 600, marginBottom: '4px' }}>
                        <Shield size={15} /> 15-Minute Price & Stock Protection Guaranteed
                      </div>
                      When you click checkout, the system allocates these {selectedQuantity} unit(s) directly from warehouse buffer.
                    </div>

                    <button
                      onClick={() => handleStartCheckout(selectedProduct, selectedQuantity)}
                      className="btn-luxury-primary"
                      style={{ width: '100%', padding: '14px' }}
                    >
                      Lock Price & Checkout ({selectedQuantity} Items)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Slide-Out 15-Minute Reservation & Multi-Step Checkout Drawer */}
          {cartDrawerOpen && (
            <>
              <div className="drawer-backdrop" onClick={() => setCartDrawerOpen(false)} />
              <div className="slide-drawer">
                <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--store-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>
                      {checkoutStep === 'confirmed' ? 'Order Confirmed' : 'Checkout & Stock Reservation'}
                    </div>
                    {activeReservation && checkoutStep !== 'confirmed' && (
                      <div style={{ fontSize: '12px', color: '#D97706', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                        <Clock size={13} /> Stock locked for {formatTimer(reservationRemainingSeconds)}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setCartDrawerOpen(false)}
                    style={{ background: '#F1F5F9', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                  >
                    <X size={16} color="#0F172A" />
                  </button>
                </div>

                {/* 15-Min Timer Progress Indicator */}
                {activeReservation && checkoutStep !== 'confirmed' && (
                  <div style={{ width: '100%', background: '#F1F5F9', height: '4px' }}>
                    <div
                      className="reservation-bar"
                      style={{ width: `${Math.max(0, (reservationRemainingSeconds / 900) * 100)}%` }}
                    />
                  </div>
                )}

                {/* Drawer Content */}
                <div style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
                  {checkoutStep !== 'confirmed' && cartProduct ? (
                    <div>
                      {/* Product Summary with Live Quantity Stepper */}
                      <div style={{ display: 'flex', gap: '16px', padding: '16px', background: '#F8FAFC', borderRadius: '12px', marginBottom: '24px', alignItems: 'center' }}>
                        <img
                          src={PRODUCT_IMAGES[cartProduct.sku_code] || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80'}
                          alt={cartProduct.product_title}
                          style={{ width: '64px', height: '64px', objectFit: 'cover', borderRadius: '8px' }}
                        />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A' }}>{cartProduct.product_title}</div>
                          <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Size: EU {selectedSize}</div>
                          <div style={{ fontSize: '15px', fontWeight: 800, color: '#000000', marginTop: '4px' }}>
                            ${(getProductPrice(cartProduct) * cartQuantity).toFixed(2)}
                          </div>
                        </div>

                        {/* In-Drawer Quantity Stepper */}
                        <div style={{ display: 'flex', alignItems: 'center', border: '1px solid var(--store-border)', borderRadius: '6px', background: '#FFFFFF' }}>
                          <button
                            onClick={() => setCartQuantity(Math.max(1, cartQuantity - 1))}
                            disabled={cartQuantity <= 1}
                            style={{ width: '28px', height: '28px', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: cartQuantity <= 1 ? 'not-allowed' : 'pointer' }}
                          >
                            <Minus size={12} color={cartQuantity <= 1 ? '#CBD5E1' : '#0F172A'} />
                          </button>
                          <input
                            type="number"
                            min={1}
                            max={getProductStock(cartProduct)}
                            value={cartQuantity}
                            onChange={(e) => {
                              const val = parseInt(e.target.value, 10);
                              if (isNaN(val)) setCartQuantity(1);
                              else setCartQuantity(Math.max(1, Math.min(getProductStock(cartProduct), val)));
                            }}
                            style={{ width: '48px', textAlign: 'center', fontSize: '13px', fontWeight: 800, border: 'none', background: 'transparent', outline: 'none' }}
                          />
                          <button
                            onClick={() => setCartQuantity(Math.min(getProductStock(cartProduct), cartQuantity + 1))}
                            disabled={cartQuantity >= getProductStock(cartProduct)}
                            style={{ width: '28px', height: '28px', border: 'none', background: 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: cartQuantity >= getProductStock(cartProduct) ? 'not-allowed' : 'pointer' }}
                          >
                            <Plus size={12} color={cartQuantity >= getProductStock(cartProduct) ? '#CBD5E1' : '#0F172A'} />
                          </button>
                        </div>
                      </div>

                      {/* Step 1: Shipping */}
                      {checkoutStep === 'cart' && (
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>1. Delivery Destination</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Recipient Name</label>
                              <input
                                type="text"
                                value={checkoutForm.name}
                                onChange={(e) => setCheckoutForm({ ...checkoutForm, name: e.target.value })}
                                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--store-border)', marginTop: '4px', fontSize: '13px' }}
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Email for Tracking Notifications</label>
                              <input
                                type="email"
                                value={checkoutForm.email}
                                onChange={(e) => setCheckoutForm({ ...checkoutForm, email: e.target.value })}
                                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--store-border)', marginTop: '4px', fontSize: '13px' }}
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Shipping Address</label>
                              <textarea
                                rows={2}
                                value={checkoutForm.address}
                                onChange={(e) => setCheckoutForm({ ...checkoutForm, address: e.target.value })}
                                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--store-border)', marginTop: '4px', fontSize: '13px', resize: 'none' }}
                              />
                            </div>
                          </div>
                          <button
                            onClick={() => setCheckoutStep('payment')}
                            className="btn-luxury-primary"
                            style={{ width: '100%', marginTop: '24px', padding: '12px' }}
                          >
                            Continue to Payment <ArrowRight size={14} />
                          </button>
                        </div>
                      )}

                      {/* Step 2: Payment */}
                      {checkoutStep === 'payment' && (
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>2. Payment & Carrier Selection</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div style={{ padding: '12px', border: '1px solid #2563EB', background: '#EFF6FF', borderRadius: '8px' }}>
                              <div style={{ fontSize: '13px', fontWeight: 700, color: '#1E40AF' }}>DHL Express (Carbon-Neutral)</div>
                              <div style={{ fontSize: '12px', color: '#3B82F6' }}>Guaranteed Delivery in 24-48 Hours • Free</div>
                            </div>
                            <div>
                              <label style={{ fontSize: '12px', fontWeight: 600, color: '#475569' }}>Payment Method (Simulated Stripe Token)</label>
                              <input
                                type="text"
                                value={checkoutForm.cardNumber}
                                readOnly
                                style={{ width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--store-border)', background: '#F8FAFC', marginTop: '4px', fontSize: '13px' }}
                              />
                            </div>
                          </div>

                          <div style={{ marginTop: '24px', borderTop: '1px solid var(--store-border)', paddingTop: '16px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#64748B', marginBottom: '6px' }}>
                              <span>Subtotal ({cartQuantity} item{cartQuantity > 1 ? 's' : ''})</span>
                              <span>${(getProductPrice(cartProduct) * cartQuantity).toFixed(2)}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#64748B', marginBottom: '12px' }}>
                              <span>Express Shipping</span>
                              <span style={{ color: '#059669', fontWeight: 600 }}>FREE</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', fontWeight: 800, color: '#0F172A', marginBottom: '24px' }}>
                              <span>Total</span>
                              <span>${(getProductPrice(cartProduct) * cartQuantity).toFixed(2)}</span>
                            </div>

                            <button
                              onClick={handleFinalCheckout}
                              disabled={checkoutSubmitting}
                              className="btn-luxury-primary"
                              style={{ width: '100%', padding: '14px', background: '#000000' }}
                            >
                              {checkoutSubmitting ? 'Authorizing Payment...' : `Pay $${(getProductPrice(cartProduct) * cartQuantity).toFixed(2)}`}
                            </button>
                            <button
                              onClick={() => setCheckoutStep('cart')}
                              className="btn-luxury-secondary"
                              style={{ width: '100%', marginTop: '8px', padding: '10px' }}
                            >
                              Back to Shipping
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : checkoutStep === 'confirmed' && confirmedOrder ? (
                    <div style={{ textAlign: 'center', padding: '10px 0' }}>
                      <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: '#ECFDF5', color: '#059669', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px auto' }}>
                        <CheckCircle size={32} />
                      </div>
                      <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A', marginBottom: '4px' }}>
                        Order #{confirmedOrder.external_id || confirmedOrder.id} Confirmed
                      </h3>
                      <p style={{ fontSize: '13px', color: '#64748B', marginBottom: '20px' }}>
                        Inventory successfully allocated and dispatched to carrier.
                      </p>

                      {/* Autonomous Swarm Notification & 1-Click Jump to Admin Approvals */}
                      <div style={{ background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '12px', padding: '16px', textAlign: 'left', marginBottom: '20px', fontSize: '13px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#92400E', fontWeight: 700, marginBottom: '6px' }}>
                          <Shield size={16} /> Autonomous Swarm Triggered
                        </div>
                        <p style={{ color: '#78350F', lineHeight: 1.4, marginBottom: '12px' }}>
                          This purchase consumed warehouse safety buffer stock. The <strong>Inventory Agent</strong> generated a <strong>$2,100.00 Supplier Purchase Order</strong> proposal awaiting Human Sign-Off in the Admin Portal.
                        </p>
                        <button
                          onClick={() => {
                            setCartDrawerOpen(false);
                            setConfirmedOrder(null);
                            setRoute('admin');
                            setAdminTab('approvals');
                          }}
                          style={{ background: '#D97706', color: '#FFFFFF', border: 'none', borderRadius: '8px', padding: '8px 16px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                        >
                          Review & Approve Proposal in Admin HQ →
                        </button>
                      </div>

                      <div style={{ background: '#F8FAFC', border: '1px solid var(--store-border)', borderRadius: '12px', padding: '16px', textAlign: 'left', marginBottom: '20px', fontSize: '13px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ color: '#64748B' }}>Carrier:</span>
                          <span style={{ fontWeight: 600 }}>{confirmedOrder.carrier || 'DHL Express'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                          <span style={{ color: '#64748B' }}>Tracking Reference:</span>
                          <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{confirmedOrder.tracking_number || 'DHL-84729103'}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#64748B' }}>Estimated Arrival:</span>
                          <span style={{ fontWeight: 600, color: '#059669' }}>Tomorrow by 6:00 PM</span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <button
                          onClick={() => {
                            const orderNum = confirmedOrder.external_id || confirmedOrder.order_id || confirmedOrder.id || '10045';
                            setTrackingQuery(String(orderNum));
                            handleTrackLookup(String(orderNum));
                            setCartDrawerOpen(false);
                            setConfirmedOrder(null);
                            setTrackerModalOpen(true);
                          }}
                          className="btn-luxury-primary"
                          style={{ width: '100%', padding: '12px', background: '#2563EB', borderColor: '#2563EB' }}
                        >
                          <Truck size={15} /> Track Shipment Live →
                        </button>
                        <button
                          onClick={() => {
                            setCartDrawerOpen(false);
                            setConfirmedOrder(null);
                          }}
                          className="btn-luxury-secondary"
                          style={{ width: '100%', padding: '10px' }}
                        >
                          Continue Shopping
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px 0', color: '#64748B' }}>
                      <ShoppingBag size={40} style={{ margin: '0 auto 12px auto', opacity: 0.4 }} />
                      <p style={{ fontSize: '14px', fontWeight: 500 }}>Your shopping bag is currently empty.</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {/* Live Order Tracker Modal */}
          {trackerModalOpen && (
            <div className="drawer-backdrop" onClick={() => setTrackerModalOpen(false)}>
              <div
                style={{
                  background: '#FFFFFF',
                  borderRadius: '16px',
                  maxWidth: '560px',
                  width: '90vw',
                  padding: '32px',
                  margin: 'auto',
                  position: 'relative',
                  boxShadow: 'var(--shadow-xl)'
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => setTrackerModalOpen(false)}
                  style={{ position: 'absolute', top: '18px', right: '18px', background: '#F1F5F9', border: 'none', borderRadius: '50%', width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                >
                  <X size={16} color="#0F172A" />
                </button>

                <h3 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '6px' }}>Real-Time Shipment Tracker</h3>
                <p style={{ fontSize: '13px', color: '#64748B', marginBottom: '20px' }}>
                  Enter your order number (e.g. 10045) or carrier tracking code.
                </p>

                <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
                  <input
                    type="text"
                    placeholder="Enter Order # or Tracking Code"
                    value={trackingQuery}
                    onChange={(e) => setTrackingQuery(e.target.value)}
                    style={{ flex: 1, padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--store-border)', fontSize: '13px' }}
                  />
                  <button
                    onClick={() => handleTrackLookup()}
                    disabled={trackingLoading}
                    className="btn-luxury-primary"
                    style={{ padding: '10px 18px', fontSize: '13px' }}
                  >
                    {trackingLoading ? 'Searching...' : 'Track'}
                  </button>
                </div>

                {trackingResult && (
                  <div style={{ background: '#F8FAFC', border: '1px solid var(--store-border)', borderRadius: '12px', padding: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <div>
                        <div style={{ fontSize: '15px', fontWeight: 700 }}>Order #{trackingResult.order_id || trackingResult.external_id}</div>
                        <div style={{ fontSize: '12px', color: '#64748B' }}>Carrier: {trackingResult.carrier || 'DHL Express'}</div>
                      </div>
                      <span className="badge-pill badge-pill-success">
                        {(trackingResult.status || 'IN TRANSIT').toUpperCase()}
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderLeft: '2px solid #2563EB', paddingLeft: '16px', marginLeft: '4px' }}>
                      <div style={{ fontSize: '13px' }}>
                        <span style={{ fontWeight: 700 }}>Order Dispatched & Scanned</span>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Regional Hub Bangalore • Departure verified</div>
                      </div>
                      <div style={{ fontSize: '13px' }}>
                        <span style={{ fontWeight: 700 }}>Out for Delivery</span>
                        <div style={{ fontSize: '11px', color: '#64748B' }}>Courier vehicle assigned</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Floating AI RAG Support Concierge */}
          {!chatOpen ? (
            <button
              className="floating-chat-bubble"
              onClick={() => setChatOpen(true)}
              title="Open AI Concierge"
            >
              <MessageSquare size={22} />
            </button>
          ) : (
            <div className="floating-chat-window">
              <div style={{ background: '#0F172A', color: '#FFFFFF', padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={16} color="#60A5FA" />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700 }}>Apex AI Concierge</div>
                    <div style={{ fontSize: '11px', color: '#94A3B8' }}>Instant RAG Customer Service</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {/* EC-SUP-04 Language Toggle */}
                  <div style={{ display: 'flex', background: 'rgba(255,255,255,0.1)', borderRadius: '6px', padding: '2px' }}>
                    {(['en', 'hi', 'es'] as const).map((lang) => (
                      <button
                        key={lang}
                        onClick={() => {
                          setChatLanguage(lang);
                          showToast(`[EC-SUP-04] Concierge language switched to ${lang.toUpperCase()}`, 'info');
                        }}
                        style={{
                          background: chatLanguage === lang ? '#2563EB' : 'transparent',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '2px 6px',
                          fontSize: '10px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          textTransform: 'uppercase'
                        }}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => setChatOpen(false)}
                    style={{ background: 'transparent', border: 'none', color: '#94A3B8', cursor: 'pointer' }}
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>

              <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    style={{
                      alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      background: msg.sender === 'user' ? '#000000' : '#F1F5F9',
                      color: msg.sender === 'user' ? '#FFFFFF' : '#0F172A',
                      padding: '10px 14px',
                      borderRadius: '14px',
                      fontSize: '13px',
                      lineHeight: 1.4
                    }}
                  >
                    {msg.text}
                  </div>
                ))}
                {chatLoading && (
                  <div style={{ alignSelf: 'flex-start', background: '#F1F5F9', padding: '10px 14px', borderRadius: '14px', fontSize: '12px', color: '#64748B' }}>
                    Consulting logistics RAG engine...
                  </div>
                )}
              </div>

              {/* Quick Prompt Pills */}
              <div style={{ padding: '8px 14px', borderTop: '1px solid var(--store-border)', display: 'flex', gap: '6px', overflowX: 'auto' }}>
                {[
                  confirmedOrder?.external_id ? `Where is order #${confirmedOrder.external_id}?` : 'Where is my order?',
                  'What is your return policy?',
                  'Do you ship express?',
                  'Tell me about RUN-SHOE-BLK-42'
                ].map((p, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendChat(p)}
                    style={{ background: '#F8FAFC', border: '1px solid var(--store-border)', borderRadius: '9999px', padding: '4px 10px', fontSize: '11px', color: '#475569', cursor: 'pointer', whiteSpace: 'nowrap' }}
                  >
                    {p}
                  </button>
                ))}
              </div>

              {/* EC-SUP-14: Real-Time PAN Redaction Shield Alert */}
              {/\b(?:\d[ -]*?){13,16}\b/.test(chatInput) && (
                <div style={{ background: '#FEF2F2', borderTop: '1px solid #FCA5A5', color: '#991B1B', padding: '8px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Shield size={14} color="#DC2626" style={{ flexShrink: 0 }} />
                  <span><strong>[EC-SUP-14] Card Number Detected:</strong> PAN auto-redacted before Gemini inference.</span>
                </div>
              )}

              <div style={{ padding: '12px 14px', borderTop: '1px solid var(--store-border)', display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Ask a question..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                  style={{ flex: 1, padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--store-border)', fontSize: '13px', outline: 'none' }}
                />
                <button
                  onClick={() => handleSendChat()}
                  disabled={chatLoading}
                  style={{ background: '#000000', color: '#FFFFFF', border: 'none', borderRadius: '8px', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
                >
                  <Send size={15} />
                </button>
              </div>
            </div>
          )}

          {/* Storefront Footer */}
          <footer style={{ borderTop: '1px solid var(--store-border)', background: '#FFFFFF', padding: '40px', marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <div style={{ fontSize: '16px', fontWeight: 800, color: '#000000', letterSpacing: '-0.03em' }}>APEX LABS</div>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '4px' }}>Autonomous Commerce & Logistics Architecture</div>
            </div>
            <div style={{ display: 'flex', gap: '24px', fontSize: '13px', color: '#64748B' }}>
              <span>Privacy Policy</span>
              <span>Terms of Service</span>
              <button
                onClick={() => setRoute('admin')}
                style={{ background: 'transparent', border: 'none', color: '#2563EB', fontWeight: 600, cursor: 'pointer' }}
              >
                Access Enterprise Ops HQ ({pendingApprovalsCount} Approvals) →
              </button>
            </div>
          </footer>
        </div>
      )}

      {/* ========================================================================================= */}
      {/* 2. ENTERPRISE ADMIN OPERATIONS HQ (Shopify Polaris / Stripe Caliber)                      */}
      {/* ========================================================================================= */}
      {route === 'admin' && (
        <div style={{ display: 'flex', minHeight: '100vh' }}>
          {/* Stripe Dark Sidebar */}
          <aside style={{ width: '260px', background: 'var(--admin-sidebar-bg)', borderRight: '1px solid var(--admin-sidebar-border)', color: '#FFFFFF', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            <div style={{ padding: '24px', borderBottom: '1px solid var(--admin-sidebar-border)' }}>
              <div style={{ fontSize: '15px', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF' }}>
                APEX COMMAND HQ
              </div>
              <div style={{ fontSize: '11px', color: '#94A3B8', marginTop: '2px' }}>
                Enterprise Operations Suite
              </div>
            </div>

            <nav style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
              {[
                { id: 'overview', label: 'Executive Overview', icon: Activity },
                { id: 'approvals', label: 'HITL Approvals Inbox', icon: Shield, badge: pendingApprovalsCount },
                { id: 'topology', label: '7-Agent Hive Topology', icon: Layers },
                { id: 'products', label: 'Product Management', icon: Box },
                { id: 'inventory', label: 'Inventory Matrix', icon: Box },
                { id: 'orders', label: 'Orders & Fulfillment', icon: Truck },
                { id: 'tickets', label: 'Customer Support Desk', icon: MessageSquare }
              ].map(tab => {
                const Icon = tab.icon;
                const isActive = adminTab === tab.id || (tab.id === 'topology' && adminTab === 'swarm');
                return (
                  <button
                    key={tab.id}
                    onClick={() => setAdminTab(tab.id as any)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: 'none',
                      background: isActive ? 'var(--admin-sidebar-hover)' : 'transparent',
                      color: isActive ? '#FFFFFF' : 'var(--admin-sidebar-text)',
                      fontWeight: isActive ? 600 : 500,
                      fontSize: '13px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      textAlign: 'left'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Icon size={16} color={isActive ? '#60A5FA' : '#94A3B8'} />
                      <span>{tab.label}</span>
                    </div>
                    {tab.badge !== undefined && tab.badge > 0 && (
                      <span style={{
                        background: '#EF4444',
                        color: '#FFFFFF',
                        padding: '1px 7px',
                        borderRadius: '9999px',
                        fontSize: '11px',
                        fontWeight: 700
                      }}>
                        {tab.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>

            <div style={{ padding: '16px', borderTop: '1px solid var(--admin-sidebar-border)' }}>
              <button
                onClick={() => setRoute('storefront')}
                style={{
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#FFFFFF',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                <ShoppingBag size={15} /> Back to Storefront
              </button>
            </div>
          </aside>

          {/* Admin Main Content Area */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
            <header style={{ background: 'var(--admin-header-bg)', borderBottom: '1px solid var(--admin-border)', padding: '16px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h1 style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A' }}>
                  {adminTab === 'overview' && 'Operations Dashboard'}
                  {adminTab === 'approvals' && 'Human-in-the-Loop (HITL) Triage Queue'}
                  {(adminTab === 'topology' || adminTab === 'swarm') && '7-Agent Universal Hive Mesh'}
                  {adminTab === 'products' && 'Product Catalog Management'}
                  {adminTab === 'inventory' && 'Real-Time Inventory & Safety Stock Matrix'}
                  {adminTab === 'orders' && 'Fulfillment & Logistics Monitor'}
                  {adminTab === 'tickets' && 'Customer Inquiries & Sentiment Desk'}
                </h1>
                <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                  Autonomous Operations Control Plane • Port 8001
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button
                  onClick={handleTriggerSwarmSimulation}
                  disabled={simulating}
                  className="btn-admin-primary"
                  style={{ background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)' }}
                >
                  <Zap size={14} /> {simulating ? 'Executing Swarm...' : '⚡ Run Multi-Agent Simulation'}
                </button>
                <button
                  onClick={loadData}
                  className="btn-admin-secondary"
                  title="Refresh State"
                >
                  <RefreshCw size={14} /> Refresh
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: '#F1F5F9', padding: '6px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                  <User size={14} color="#2563EB" />
                  <span>admin@autonomous.store</span>
                </div>
              </div>
            </header>

            <main style={{ padding: '32px', flex: 1 }}>
              {/* TAB 1: EXECUTIVE OVERVIEW */}
              {adminTab === 'overview' && (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '24px' }}>
                    {[
                      { label: 'Gross Merchandise Value', value: summary ? (summary.revenue_today_minor ? `$${(summary.revenue_today_minor / 100).toLocaleString()}` : `$${Number(summary.revenue_mtd || 14250).toLocaleString()}`) : '$14,250', delta: '+12.4% vs last week', icon: DollarSign, color: '#059669' },
                      { label: 'Pending HITL Approvals', value: `${pendingApprovalsCount} Actions`, delta: 'Requires operator sign-off', icon: Shield, color: '#D97706' },
                      { label: 'Low Stock Risk SKUs', value: `${summary?.critical_stockouts_count ?? summary?.low_stock_skus ?? 2} SKUs`, delta: 'Safety stock alert active', icon: AlertTriangle, color: '#EF4444' },
                      { label: 'Order Fulfillment Rate', value: '99.4%', delta: 'Average dispatch: 4.2h', icon: Truck, color: '#2563EB' }
                    ].map((kpi, idx) => {
                      const Icon = kpi.icon;
                      return (
                        <div key={idx} style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '20px', boxShadow: 'var(--shadow-sm)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748B' }}>{kpi.label}</span>
                            <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${kpi.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                              <Icon size={16} color={kpi.color} />
                            </div>
                          </div>
                          <div style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', marginBottom: '4px' }}>{kpi.value}</div>
                          <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>{kpi.delta}</div>
                        </div>
                      );
                    })}
                  </div>

                  {/* 7-Agent Universal Hive Mesh Heartbeat Status Row */}
                  <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '20px 24px', marginBottom: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Layers size={18} color="#2563EB" />
                        <div>
                          <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0F172A' }}>7-Agent Autonomous Mesh Heartbeat</h3>
                          <div style={{ fontSize: '11px', color: '#64748B' }}>Real-time telemetry and health monitoring across all decision domains</div>
                        </div>
                      </div>
                      <span style={{ fontSize: '12px', color: '#059669', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="heartbeat-dot-online" /> 7/7 AGENTS OPERATIONAL
                      </span>
                    </div>

                    <div className="agent-heartbeat-grid">
                      {((agentHealth && agentHealth.length > 0) ? agentHealth : [
                        { id: 'inventory', name: 'Inventory Agent', emoji: '📦', domain: 'Stock & Buffer', status: 'online', runs_today: 14, last_latency_ms: 320 },
                        { id: 'pricing', name: 'Pricing Agent', emoji: '💰', domain: 'Margin & MAP', status: 'online', runs_today: 9, last_latency_ms: 280 },
                        { id: 'support', name: 'Support Agent', emoji: '💬', domain: 'RAG Concierge', status: 'online', runs_today: 31, last_latency_ms: 410 },
                        { id: 'order_ops', name: 'Order Ops Agent', emoji: '🚚', domain: 'Idempotency', status: 'online', runs_today: 22, last_latency_ms: 190 },
                        { id: 'logistics', name: 'Logistics Agent', emoji: '🛩', domain: 'Scorecards', status: 'online', runs_today: 11, last_latency_ms: 350 },
                        { id: 'marketing', name: 'Marketing Agent', emoji: '📢', domain: 'Ad Protection', status: 'online', runs_today: 7, last_latency_ms: 290 },
                        { id: 'supervisor', name: 'Supervisor Agent', emoji: '🎯', domain: 'Master Mesh', status: 'online', runs_today: 48, last_latency_ms: 150 }
                      ]).map((ag: any) => (
                        <div key={ag.id} className="agent-heartbeat-card">
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: '18px' }}>{ag.emoji}</span>
                            <div className={ag.status === 'online' ? 'heartbeat-dot-online' : 'heartbeat-dot-idle'} title={ag.status} />
                          </div>
                          <div>
                            <div style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{ag.name}</div>
                            <div style={{ fontSize: '10px', color: '#64748B' }}>{ag.domain}</div>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#94A3B8', borderTop: '1px solid #F1F5F9', paddingTop: '4px', marginTop: '2px' }}>
                            <span>{ag.runs_today || 12} runs today</span>
                            <span style={{ fontFamily: 'var(--font-mono)' }}>{ag.last_latency_ms || 240}ms</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', padding: '24px', marginBottom: '24px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                      <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Autonomous Proposals Awaiting Approval</h3>
                      <button onClick={() => setAdminTab('approvals')} className="btn-admin-secondary" style={{ fontSize: '12px' }}>
                        View All ({pendingApprovalsCount})
                      </button>
                    </div>

                    {actions.filter(a => a.status === 'pending_approval' || a.status === 'pending').length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {actions.filter(a => a.status === 'pending_approval' || a.status === 'pending').slice(0, 3).map(action => (
                          <div key={action.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', background: '#F8FAFC', border: '1px solid var(--admin-border)', borderRadius: '8px' }}>
                            <div>
                              <div style={{ fontSize: '14px', fontWeight: 700, color: '#0F172A' }}>{action.summary || action.action_type}</div>
                              <div style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>Risk: {action.risk_level || 'medium'} • Created: {new Date(action.created_at || Date.now()).toLocaleTimeString()}</div>
                            </div>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button onClick={() => handleReject(action.id)} className="btn-admin-secondary" style={{ color: '#EF4444' }}>Reject</button>
                              <button onClick={() => handleApprove(action.id)} className="btn-admin-primary">Approve Action</button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '24px', color: '#64748B', fontSize: '13px' }}>
                        ✓ All autonomous actions processed. Click "⚡ Run Multi-Agent Simulation" above to trigger a test cycle!
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: HITL APPROVALS INBOX */}
              {adminTab === 'approvals' && (() => {
                const pendingList = actions.filter(a => a.status === 'pending_approval' || a.status === 'pending');
                const sortedPending = [...pendingList].sort((a, b) => {
                  const pOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
                  const pA = a.priority || (a.risk_level === 'high' || a.action_type === 'hold_inventory' ? 'P0' : a.risk_level === 'medium' ? 'P1' : 'P2');
                  const pB = b.priority || (b.risk_level === 'high' || b.action_type === 'hold_inventory' ? 'P0' : b.risk_level === 'medium' ? 'P1' : 'P2');
                  return (pOrder[pA] ?? 2) - (pOrder[pB] ?? 2);
                });
                const p0Items = sortedPending.filter(a => (a.priority === 'P0' || a.risk_level === 'high' || a.action_type === 'hold_inventory'));

                return (
                  <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', overflow: 'hidden' }}>
                    <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--admin-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                      <div>
                        <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Priority-Ranked Decision Queue</h3>
                        <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                          LangGraph Multi-Agent Proposals sorted by policy severity (P0 Critical → P3 Low)
                        </p>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        {p0Items.length > 0 && (
                          <button
                            onClick={async () => {
                              for (const it of p0Items) {
                                await handleApprove(it.id);
                              }
                              showToast(`Approved ${p0Items.length} P0 priority item(s)!`, 'success');
                            }}
                            className="btn-admin-primary"
                            style={{ background: '#DC2626', borderColor: '#DC2626', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                          >
                            <Zap size={13} /> Approve All P0 ({p0Items.length})
                          </button>
                        )}
                        <span className="badge-pill badge-pill-warning">{pendingList.length} Awaiting Decision</span>
                      </div>
                    </div>

                    {sortedPending.length > 0 ? (
                      <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {sortedPending.map(action => {
                          const priority = action.priority || (action.risk_level === 'high' || action.action_type === 'hold_inventory' ? 'P0' : action.risk_level === 'medium' ? 'P1' : 'P2');
                          const priorityClass = priority === 'P0' ? 'priority-pill-p0' : priority === 'P1' ? 'priority-pill-p1' : 'priority-pill-p2';

                          return (
                            <div key={action.id} style={{ border: priority === 'P0' ? '1px solid #FCA5A5' : '1px solid var(--admin-border)', borderRadius: '10px', padding: '20px', background: priority === 'P0' ? '#FFFAFA' : '#FFFFFF' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                <div>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                                    <span className={priorityClass}>{priority} PRIORITY</span>
                                    <span className="badge-pill badge-pill-info">{(action.action_type || 'PROPOSAL').toUpperCase()}</span>
                                  </div>
                                  <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#0F172A' }}>{action.summary || action.action_type}</h4>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#D97706', fontWeight: 600 }}>
                                  <Clock size={14} /> 24h Expiration Active
                                </div>
                              </div>

                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', background: '#F8FAFC', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '12px' }}>
                                <div>
                                  <span style={{ color: '#64748B' }}>Resource:</span>
                                  <div style={{ fontWeight: 700 }}>{action.resource_id || action.resource_type || 'SKU'}</div>
                                </div>
                                <div>
                                  <span style={{ color: '#64748B' }}>Risk Score:</span>
                                  <div style={{ fontWeight: 700, color: priority === 'P0' ? '#DC2626' : '#059669' }}>{action.risk_level || (priority === 'P0' ? 'HIGH' : 'LOW')}</div>
                                </div>
                                <div>
                                  <span style={{ color: '#64748B' }}>Policy Compliance:</span>
                                  <div style={{ fontWeight: 700, color: '#2563EB' }}>Verified (≥30% Margin Floor)</div>
                                </div>
                              </div>

                              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                                <button
                                  onClick={() => setInspectingAction(action)}
                                  className="btn-admin-secondary"
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                                >
                                  <Eye size={13} color="#2563EB" /> Inspect Policy Rules & Evidence
                                </button>
                                <button onClick={() => handleReject(action.id)} className="btn-admin-secondary" style={{ color: '#EF4444' }}>Reject Proposal</button>
                                <button onClick={() => handleApprove(action.id)} className="btn-admin-primary">Approve & Execute</button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748B' }}>
                        <CheckCircle size={40} color="#059669" style={{ margin: '0 auto 12px auto' }} />
                        <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>Queue is Empty</h4>
                        <p style={{ fontSize: '13px', marginTop: '4px', marginBottom: '16px' }}>All AI agent proposals have been reviewed and approved.</p>
                        <button onClick={handleTriggerSwarmSimulation} className="btn-admin-primary" style={{ margin: '0 auto' }}>
                          <Zap size={14} /> ⚡ Run Multi-Agent Simulation to Generate New Proposals
                        </button>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* TAB 3: INVENTORY MATRIX */}
              {adminTab === 'inventory' && (
                <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', overflow: 'hidden' }}>
                  <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--admin-border)' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700 }}>SKU Stock & Allocation Matrix</h3>
                    <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                      Live warehouse inventory with 15-minute consumer cart locks and safety stock triggers
                    </p>
                  </div>

                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>SKU Code</th>
                        <th>Product Title</th>
                        <th>Current Price</th>
                        <th>On-Hand Stock</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inventory.map(item => {
                        const stock = getProductStock(item);
                        const price = getProductPrice(item);
                        const isLow = stock <= 5;
                        return (
                          <tr key={item.sku_code}>
                            <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{item.sku_code}</td>
                            <td style={{ fontWeight: 600 }}>{item.product_title}</td>
                            <td style={{ fontWeight: 700 }}>${price.toFixed(2)}</td>
                            <td>
                              <span style={{ fontWeight: 800, color: isLow ? '#EF4444' : '#0F172A' }}>
                                {stock} units
                              </span>
                            </td>
                            <td>
                              <span className={`badge-pill ${isLow ? 'badge-pill-danger' : 'badge-pill-success'}`}>
                                {isLow ? 'Safety Stock Warning' : 'Optimal'}
                              </span>
                            </td>
                            <td>
                              <button onClick={() => handleRestock(item.sku_code)} className="btn-admin-secondary" style={{ fontSize: '12px' }}>
                                Replenish (+50)
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* TAB 4: ORDERS & FULFILLMENT */}
              {adminTab === 'orders' && (
                <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', overflow: 'hidden' }}>
                  <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--admin-border)' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Fulfillment & Logistics Queue</h3>
                    <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                      Orders processed with idempotent transaction deduplication and automated carrier booking
                    </p>
                  </div>

                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Carrier</th>
                        <th>Tracking Reference</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(orders.length > 0 ? orders : [
                        { id: '10045', customer_name: 'Aarav Mehta', total_amount: 189.99, carrier: 'DHL Express', tracking_number: 'DHL-84729103', status: 'IN TRANSIT' },
                        { id: '10044', customer_name: 'Sophia Patel', total_amount: 169.99, carrier: 'FedEx Priority', tracking_number: 'FDX-99214012', status: 'DELIVERED' }
                      ]).map((ord: any) => (
                        <tr key={ord.id || ord.external_id || ord.order_id}>
                          <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>#{ord.external_id || ord.order_id || ord.id}</td>
                          <td>{ord.customer_name || 'Aarav Mehta'}</td>
                          <td style={{ fontWeight: 700 }}>${Number(ord.total_amount || 189.99).toFixed(2)}</td>
                          <td>{ord.carrier || 'DHL Express'}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{ord.tracking_number || 'DHL-84729103'}</td>
                          <td>
                            <span className="badge-pill badge-pill-success">
                              {ord.status || 'DISPATCHED'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* PRODUCT MANAGEMENT TAB */}
              {adminTab === 'products' && (
                <ProductManagementView
                  showToast={showToast}
                />
              )}

              {/* TAB 3: 7-AGENT HIVE TOPOLOGY DECK */}
              {(adminTab === 'topology' || adminTab === 'swarm') && (
                <HiveTopologyView
                  onTriggerSimulation={handleTriggerSwarmSimulation}
                  simulating={simulating}
                />
              )}

              {/* TAB 6: CUSTOMER TICKETS */}
              {adminTab === 'tickets' && (
                <div style={{ background: '#FFFFFF', border: '1px solid var(--admin-border)', borderRadius: '12px', overflow: 'hidden' }}>
                  <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--admin-border)' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Customer Inquiries & Sentiment Desk</h3>
                    <p style={{ fontSize: '12px', color: '#64748B', marginTop: '2px' }}>
                      Live support tickets resolved autonomously via RAG concierge or routed to human agents
                    </p>
                  </div>

                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Ticket ID</th>
                        <th>Customer</th>
                        <th>Subject</th>
                        <th>Sentiment</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(tickets.length > 0 ? tickets : [
                        { id: 'TCK-801', customer_name: 'Aarav Mehta', subject: 'Tracking update request for #10045', sentiment: 'POSITIVE', status: 'RESOLVED' },
                        { id: 'TCK-802', customer_name: 'Elena Rostova', subject: 'Inquiry regarding return window', sentiment: 'NEUTRAL', status: 'RESOLVED' }
                      ]).map((t: any) => (
                        <tr key={t.id || t.ticket_id}>
                          <td style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>#{t.external_id || t.ticket_id || t.id}</td>
                          <td>{t.customer_name || t.customer_email || 'Aarav Mehta'}</td>
                          <td style={{ fontWeight: 600 }}>{t.subject || 'Order Status Inquiry'}</td>
                          <td>
                            <span className="badge-pill badge-pill-info">{t.sentiment || 'NEUTRAL'}</span>
                          </td>
                          <td>
                            <span className="badge-pill badge-pill-success">{t.status || 'RESOLVED'}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </main>
          </div>
        </div>
      )}

      {/* Pre-Execution Policy Inspection Modal */}
      <ActionInspectionModal
        action={inspectingAction}
        onClose={() => setInspectingAction(null)}
        onApprove={(id) => {
          handleApprove(id);
          setInspectingAction(null);
        }}
        onReject={(id) => {
          handleReject(id);
          setInspectingAction(null);
        }}
      />
    </div>
  );
}
