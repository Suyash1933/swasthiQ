import { useDeferredValue, useEffect, useState } from 'react'
import axios from 'axios'
import {
  BrowserRouter,
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom'
import './App.css'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
})

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const numberFormatter = new Intl.NumberFormat('en-IN')

const emptyMedicine = {
  name: '',
  generic_name: '',
  manufacturer: '',
  supplier_name: '',
  category: '',
  dosage_form: 'Tablet',
  strength: '',
  batch_number: '',
  quantity: 0,
  unit_price: '',
  reorder_level: 10,
  expiry_date: '',
  location: '',
  manual_expired: false,
}

const navItems = [
  { label: 'Dashboard', path: '/', icon: 'grid' },
  { label: 'Inventory', path: '/inventory', icon: 'inventory' },
]

const railIcons = ['search', 'menu', 'pulse', 'users', 'stethoscope', 'pill']
const quickTabs = [
  { label: 'Sales', icon: 'sales' },
  { label: 'Purchase', icon: 'purchase' },
  { label: 'Inventory', icon: 'inventory' },
]
const statusOptions = [
  { label: 'All status', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Low stock', value: 'low_stock' },
  { label: 'Expired', value: 'expired' },
  { label: 'Out of stock', value: 'out_of_stock' },
]

function App() {
  return (
    <BrowserRouter>
      <Workspace />
    </BrowserRouter>
  )
}

function Workspace() {
  const [refreshTick, setRefreshTick] = useState(0)

  return (
    <div className="crm-scene">
      <Sidebar />
      <main className="crm-main">
        <div className="crm-canvas">
          <Routes>
            <Route
              index
              element={<DashboardPage refreshTick={refreshTick} />}
            />
            <Route
              path="/inventory"
              element={
                <InventoryPage
                  refreshTick={refreshTick}
                  onInventoryChange={() => setRefreshTick((value) => value + 1)}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function Sidebar() {
  const navigate = useNavigate()

  return (
    <aside className="sidebar">
      <div className="sidebar__panel">
        <div className="sidebar__top">
          <button className="rail-button rail-button--ghost" type="button">
            <AppIcon name="search" />
          </button>

          {navItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `rail-button rail-button--nav${isActive ? ' is-active' : ''}`
              }
              title={item.label}
            >
              <AppIcon name={item.icon} />
            </NavLink>
          ))}

          {railIcons.slice(1).map((name) => (
            <button
              key={name}
              className="rail-button rail-button--ghost"
              type="button"
              title={name}
            >
              <AppIcon name={name} />
            </button>
          ))}

          <button
            className="rail-button rail-button--primary"
            type="button"
            onClick={() => navigate('/inventory')}
            title="Add medicine"
          >
            <AppIcon name="plus" />
          </button>

          <button className="rail-button rail-button--ghost" type="button">
            <AppIcon name="spark" />
          </button>
        </div>

        <div className="sidebar__bottom">
          <button className="rail-button rail-button--ghost" type="button">
            <AppIcon name="settings" />
          </button>
        </div>
      </div>
    </aside>
  )
}

function DashboardPage({ refreshTick }) {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [patientId, setPatientId] = useState('')
  const [saleSearch, setSaleSearch] = useState('')
  const [saleItems, setSaleItems] = useState([])
  const [saleLoading, setSaleLoading] = useState(true)
  const [saleError, setSaleError] = useState('')
  const [selectedSaleItems, setSelectedSaleItems] = useState([])
  const [billingMessage, setBillingMessage] = useState('')
  const [billingLoading, setBillingLoading] = useState(false)
  const [saleRefreshTick, setSaleRefreshTick] = useState(0)

  const deferredSaleSearch = useDeferredValue(saleSearch)

  useEffect(() => {
    let ignore = false

    async function loadOverview() {
      setLoading(true)
      setError('')

      try {
        const response = await api.get('/dashboard/overview')
        if (!ignore) {
          setOverview(response.data.data)
        }
      } catch (requestError) {
        if (!ignore) {
          setError(extractApiError(requestError))
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    }

    loadOverview()

    return () => {
      ignore = true
    }
  }, [refreshTick, saleRefreshTick])

  useEffect(() => {
    let ignore = false

    async function loadSaleItems() {
      setSaleLoading(true)
      setSaleError('')

      try {
        const params = {}

        if (deferredSaleSearch.trim()) {
          params.search = deferredSaleSearch.trim()
        }

        const response = await api.get('/medicines', { params })
        if (!ignore) {
          setSaleItems(response.data.data)
        }
      } catch (requestError) {
        if (!ignore) {
          setSaleError(extractApiError(requestError))
        }
      } finally {
        if (!ignore) {
          setSaleLoading(false)
        }
      }
    }

    loadSaleItems()

    return () => {
      ignore = true
    }
  }, [deferredSaleSearch, refreshTick, saleRefreshTick])

  const preparedAmount = selectedSaleItems.reduce(
    (total, item) => total + Number(item.unit_price || 0) * Number(item.saleQuantity || 1),
    0,
  )
  const preparedUnits = selectedSaleItems.reduce(
    (total, item) => total + Number(item.saleQuantity || 1),
    0,
  )

  function toggleSaleItem(item) {
    setSelectedSaleItems((current) => {
      const exists = current.some((entry) => entry.id === item.id)
      if (exists) {
        return current.filter((entry) => entry.id !== item.id)
      }

      return [...current, { ...item, saleQuantity: 1 }]
    })
  }

  function updateSaleQuantity(medicineId, nextQuantity, maxQuantity) {
    const parsedQuantity = Number(nextQuantity)
    const safeQuantity = Number.isFinite(parsedQuantity)
      ? Math.min(Math.max(parsedQuantity, 1), Math.max(maxQuantity, 1))
      : 1

    setSelectedSaleItems((current) =>
      current.map((item) =>
        item.id === medicineId
          ? { ...item, saleQuantity: safeQuantity }
          : item,
      ),
    )
  }

  async function handleBillPreview() {
    if (!patientId.trim()) {
      setSaleError('Enter a patient id before billing.')
      return
    }

    if (!selectedSaleItems.length) {
      setSaleError('Select at least one medicine to create a bill.')
      return
    }

    setBillingLoading(true)
    setSaleError('')
    setBillingMessage('')

    try {
      const response = await api.post('/sales/bill', {
        patient_id: patientId.trim(),
        items: selectedSaleItems.map((item) => ({
          medicine_id: item.id,
          quantity: Number(item.saleQuantity || 1),
        })),
      })

      setBillingMessage(
        `Bill ${response.data.data.invoice_number} created for patient ${patientId.trim()} with ${preparedUnits} units worth ${formatCurrency(preparedAmount)}.`,
      )
      setSelectedSaleItems([])
      setPatientId('')
      setSaleSearch('')
      setSaleRefreshTick((value) => value + 1)
    } catch (requestError) {
      setSaleError(extractApiError(requestError))
    } finally {
      setBillingLoading(false)
    }
  }

  function handleExport() {
    if (!overview) {
      return
    }

    downloadJson(overview, 'dashboard-overview.json')
  }

  return (
    <section className="page">
      <PageHeader
        eyebrow="Live REST Data"
        title="Pharmacy CRM"
        subtitle="Manage inventory, sales, and purchase orders with the SwasthiQ pharmacy workspace."
        actions={
          <>
            <button className="action-button" type="button" onClick={handleExport}>
              <AppIcon name="export" />
              Export
            </button>
            <NavLink className="action-button action-button--primary" to="/inventory">
              <AppIcon name="plus" />
              Add Medicine
            </NavLink>
          </>
        }
      />

      {error ? <NoticeBanner tone="error" message={error} /> : null}
      {billingMessage ? <NoticeBanner tone="info" message={billingMessage} /> : null}

      <div className="metric-grid">
        <MetricCard
          tone="success"
          icon="money"
          label="Today's Sales"
          value={loading || !overview ? 'Loading...' : formatCurrency(overview.sales_summary.total_sales_amount)}
          badge={loading || !overview ? null : `+${overview.sales_summary.transaction_count} bills`}
        />
        <MetricCard
          tone="primary"
          icon="sales"
          label="Items Sold Today"
          value={loading || !overview ? 'Loading...' : numberFormatter.format(overview.items_sold.total_units_sold)}
          badge={loading || !overview ? null : `${overview.items_sold.unique_medicines_sold} SKUs`}
        />
        <MetricCard
          tone="warning"
          icon="warning"
          label="Low Stock Items"
          value={loading || !overview ? 'Loading...' : numberFormatter.format(overview.low_stock_items.length)}
          badge="Action needed"
        />
        <MetricCard
          tone="accent"
          icon="box"
          label="Purchase Orders"
          value={loading || !overview ? 'Loading...' : formatCurrency(overview.purchase_order_summary.pending_value)}
          badge={loading || !overview ? null : `${overview.purchase_order_summary.pending_count} pending`}
        />
      </div>

      <section className="panel">
        <div className="panel__toolbar">
          <div className="segmented-control">
            {quickTabs.map((tab) => (
              <button
                key={tab.label}
                className={`segment${tab.label === 'Sales' ? ' is-active' : ''}`}
                type="button"
              >
                <AppIcon name={tab.icon} />
                {tab.label}
              </button>
            ))}
          </div>

          <div className="panel__actions">
            <button className="action-button action-button--primary" type="button">
              <AppIcon name="plus" />
              New Sale
            </button>
            <NavLink className="action-button" to="/inventory">
              <AppIcon name="purchase" />
              New Purchase
            </NavLink>
          </div>
        </div>

        <div className="sales-workbench">
          <div className="sales-workbench__header">
            <div>
              <h2>Make a Sale</h2>
              <p>Select medicines from live inventory and prepare a billing preview.</p>
            </div>
            <div className="summary-chip">
              {selectedSaleItems.length} medicines | {preparedUnits} units | {formatCurrency(preparedAmount)}
            </div>
          </div>

          <div className="sales-fields">
            <label className="field">
              <span className="field__label">Patient ID</span>
              <input
                type="text"
                value={patientId}
                onChange={(event) => setPatientId(event.target.value)}
                placeholder="Enter patient id"
              />
            </label>

            <label className="field field--wide">
              <span className="field__label">Search medicines</span>
              <div className="search-input">
                <AppIcon name="search" />
                <input
                  type="search"
                  value={saleSearch}
                  onChange={(event) => setSaleSearch(event.target.value)}
                  placeholder="Search medicines, supplier, or batch..."
                />
              </div>
            </label>

            <button
              className="action-button action-button--primary"
              type="button"
              onClick={() => setSaleSearch('')}
            >
              Show All
            </button>

            <button
              className="action-button action-button--danger"
              type="button"
              onClick={handleBillPreview}
              disabled={!selectedSaleItems.length || billingLoading}
            >
              {billingLoading ? 'Billing...' : 'Bill'}
            </button>
          </div>

          {saleError ? <NoticeBanner tone="error" message={saleError} /> : null}

          <div className="table-shell table-shell--sales">
            <div className="table-scroller">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Medicine Name</th>
                    <th>Generic Name</th>
                    <th>Batch No</th>
                    <th>Expiry Date</th>
                    <th>Quantity</th>
                    <th>MRP / Price</th>
                    <th>Supplier</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {saleLoading ? (
                    <tr>
                      <td colSpan="9" className="table-empty">
                        Loading live inventory...
                      </td>
                    </tr>
                  ) : saleItems.length ? (
                    saleItems.map((medicine) => {
                      const selectedEntry = selectedSaleItems.find(
                        (entry) => entry.id === medicine.id,
                      )
                      const isSelected = Boolean(selectedEntry)
                      const isBlocked =
                        medicine.status === 'expired' || medicine.status === 'out_of_stock'

                      return (
                        <tr key={medicine.id}>
                          <td>{medicine.name}</td>
                          <td>{medicine.generic_name}</td>
                          <td>{medicine.batch_number}</td>
                          <td>{formatShortDate(medicine.expiry_date)}</td>
                          <td>{numberFormatter.format(medicine.quantity)}</td>
                          <td>{formatCurrency(medicine.unit_price)}</td>
                          <td>{medicine.supplier_name}</td>
                          <td>
                            <StatusPill status={medicine.status} />
                          </td>
                          <td>
                            {isBlocked ? (
                              <span className="table-status-note">
                                {medicine.status === 'expired'
                                  ? 'Expired'
                                  : 'Out of stock'}
                              </span>
                            ) : isSelected ? (
                              <div className="sale-row-actions">
                                <input
                                  className="sale-qty-input"
                                  type="number"
                                  min="1"
                                  max={medicine.quantity}
                                  value={selectedEntry.saleQuantity}
                                  onChange={(event) =>
                                    updateSaleQuantity(
                                      medicine.id,
                                      event.target.value,
                                      medicine.quantity,
                                    )
                                  }
                                />
                                <button
                                  className="table-action"
                                  type="button"
                                  onClick={() => toggleSaleItem(medicine)}
                                >
                                  Remove
                                </button>
                              </div>
                            ) : (
                              <button
                                className="table-action"
                                type="button"
                                onClick={() => toggleSaleItem(medicine)}
                              >
                                Add
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan="9" className="table-empty">
                        No medicines matched your search.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Recent Sales</h2>
            <p>Latest completed transactions flowing in from the backend.</p>
          </div>
        </div>

        <div className="sales-list">
          {loading ? (
            <div className="empty-card">Loading recent sales...</div>
          ) : overview?.recent_sales?.length ? (
            overview.recent_sales.map((sale) => (
              <article key={sale.id} className="sale-card">
                <div className="sale-card__icon">
                  <AppIcon name="sales" />
                </div>

                <div className="sale-card__body">
                  <h3>{sale.invoice_number}</h3>
                  <p>
                    Patient: {sale.customer_name} | {sale.item_count} items | {sale.payment_method}
                  </p>
                  <span>{sale.medicine_name}</span>
                </div>

                <div className="sale-card__meta">
                  <strong>{formatCurrency(sale.total_amount)}</strong>
                  <span>{formatDateTime(sale.sold_at)}</span>
                  <StatusPill status="active" label="Completed" />
                </div>
              </article>
            ))
          ) : (
            <div className="empty-card">No recent sales available right now.</div>
          )}
        </div>
      </section>
    </section>
  )
}

function InventoryPage({ refreshTick, onInventoryChange }) {
  const [summary, setSummary] = useState(null)
  const [medicines, setMedicines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [composerOpen, setComposerOpen] = useState(false)
  const [composerMode, setComposerMode] = useState('create')
  const [formState, setFormState] = useState(emptyMedicine)
  const [formError, setFormError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const deferredSearch = useDeferredValue(searchTerm)
  const categories = Array.from(new Set(medicines.map((medicine) => medicine.category))).sort()
  const selectedMedicine =
    medicines.find((medicine) => medicine.id === selectedId) ?? null

  async function loadInventory() {
    setLoading(true)
    setError('')

    try {
      const params = {}

      if (deferredSearch.trim()) {
        params.search = deferredSearch.trim()
      }

      if (statusFilter) {
        params.status = statusFilter
      }

      if (categoryFilter) {
        params.category = categoryFilter
      }

      const [summaryResponse, medicinesResponse] = await Promise.all([
        api.get('/inventory/summary'),
        api.get('/medicines', { params }),
      ])

      const nextMedicines = medicinesResponse.data.data
      setSummary(summaryResponse.data.data)
      setMedicines(nextMedicines)
      setSelectedId((current) =>
        nextMedicines.some((medicine) => medicine.id === current)
          ? current
          : nextMedicines[0]?.id ?? null,
      )
    } catch (requestError) {
      setError(extractApiError(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInventory()
  }, [deferredSearch, statusFilter, categoryFilter, refreshTick])

  function openCreateComposer() {
    setComposerMode('create')
    setComposerOpen(true)
    setFormError('')
    setFormState({
      ...emptyMedicine,
      expiry_date: getDefaultExpiryDate(),
    })
  }

  function openEditComposer(medicine = selectedMedicine) {
    if (!medicine) {
      return
    }

    setComposerMode('edit')
    setComposerOpen(true)
    setFormError('')
    setFormState(toMedicineFormState(medicine))
  }

  function closeComposer() {
    setComposerOpen(false)
    setFormError('')
  }

  function handleFieldChange(event) {
    const { name, value, type, checked } = event.target

    setFormState((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  async function handleFormSubmit(event) {
    event.preventDefault()
    setSubmitting(true)
    setFormError('')

    try {
      const payload = toMedicinePayload(formState)

      if (composerMode === 'create') {
        await api.post('/medicines', payload)
        setActionMessage('Medicine created successfully.')
      } else if (selectedMedicine) {
        await api.put(`/medicines/${selectedMedicine.id}`, payload)
        setActionMessage('Medicine updated successfully.')
      }

      setComposerOpen(false)
      await loadInventory()
      onInventoryChange()
    } catch (requestError) {
      setFormError(extractApiError(requestError))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleStatusChange(nextStatus) {
    if (!selectedMedicine) {
      return
    }

    setActionMessage('')
    setError('')

    try {
      await api.patch(`/medicines/${selectedMedicine.id}/status`, {
        status: nextStatus,
      })
      setActionMessage(`Medicine marked as ${nextStatus.replace('_', ' ')}.`)
      await loadInventory()
      onInventoryChange()
    } catch (requestError) {
      setError(extractApiError(requestError))
    }
  }

  return (
    <section className="page">
      <PageHeader
        eyebrow="Inventory Module"
        title="Inventory Control"
        subtitle="Search, filter, add, and update medicines with live FastAPI-backed inventory data."
        actions={
          <>
            <button className="action-button" type="button" onClick={loadInventory}>
              <AppIcon name="refresh" />
              Refresh
            </button>
            <button
              className="action-button action-button--primary"
              type="button"
              onClick={openCreateComposer}
            >
              <AppIcon name="plus" />
              Add Medicine
            </button>
          </>
        }
      />

      {error ? <NoticeBanner tone="error" message={error} /> : null}
      {actionMessage ? <NoticeBanner tone="success" message={actionMessage} /> : null}

      <div className="metric-grid metric-grid--inventory">
        <MetricCard
          tone="primary"
          icon="inventory"
          label="Total Medicines"
          value={loading || !summary ? 'Loading...' : numberFormatter.format(summary.total_medicines)}
          badge="Live stock"
        />
        <MetricCard
          tone="success"
          icon="check"
          label="Active"
          value={loading || !summary ? 'Loading...' : numberFormatter.format(summary.active)}
          badge="Ready to sell"
        />
        <MetricCard
          tone="warning"
          icon="warning"
          label="Low Stock"
          value={loading || !summary ? 'Loading...' : numberFormatter.format(summary.low_stock)}
          badge="Needs reorder"
        />
        <MetricCard
          tone="accent"
          icon="box"
          label="Expired"
          value={loading || !summary ? 'Loading...' : numberFormatter.format(summary.expired)}
          badge="Check immediately"
        />
        <MetricCard
          tone="muted"
          icon="money"
          label="Inventory Value"
          value={loading || !summary ? 'Loading...' : formatCurrency(summary.total_inventory_value)}
          badge="At MRP"
        />
      </div>

      <section className="panel">
        <div className="filters">
          <label className="field field--wide">
            <span className="field__label">Search inventory</span>
            <div className="search-input">
              <AppIcon name="search" />
              <input
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search medicine, generic name, supplier, batch..."
              />
            </div>
          </label>

          <label className="field">
            <span className="field__label">Status</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {statusOptions.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span className="field__label">Category</span>
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <div className="inventory-layout">
        <section className="panel inventory-table">
          <div className="section-heading">
            <div>
              <h2>Medicine Inventory</h2>
              <p>{loading ? 'Loading medicines...' : `${medicines.length} medicines visible`}</p>
            </div>
          </div>

          <div className="table-scroller">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Medicine</th>
                  <th>Generic Name</th>
                  <th>Batch</th>
                  <th>Stock</th>
                  <th>MRP</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="7" className="table-empty">
                      Loading inventory...
                    </td>
                  </tr>
                ) : medicines.length ? (
                  medicines.map((medicine) => (
                    <tr
                      key={medicine.id}
                      className={medicine.id === selectedId ? 'is-highlighted' : ''}
                      onClick={() => setSelectedId(medicine.id)}
                    >
                      <td>
                        <div className="table-title">
                          <strong>{medicine.name}</strong>
                          <span>{medicine.manufacturer}</span>
                        </div>
                      </td>
                      <td>{medicine.generic_name}</td>
                      <td>{medicine.batch_number}</td>
                      <td>{numberFormatter.format(medicine.quantity)}</td>
                      <td>{formatCurrency(medicine.unit_price)}</td>
                      <td>
                        <StatusPill status={medicine.status} />
                      </td>
                      <td>
                        <button
                          className="table-action"
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation()
                            setSelectedId(medicine.id)
                            openEditComposer(medicine)
                          }}
                        >
                          Edit
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" className="table-empty">
                      No medicines found for the selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel inventory-sidecard">
          {composerOpen ? (
            <>
              <div className="section-heading">
                <div>
                  <h2>{composerMode === 'create' ? 'Add Medicine' : 'Update Medicine'}</h2>
                  <p>Use real backend validation before saving any inventory changes.</p>
                </div>
                <button className="action-button" type="button" onClick={closeComposer}>
                  Close
                </button>
              </div>

              {formError ? <NoticeBanner tone="error" message={formError} /> : null}

              <form className="medicine-form" onSubmit={handleFormSubmit}>
                <div className="form-grid">
                  <label className="field">
                    <span className="field__label">Medicine name</span>
                    <input name="name" value={formState.name} onChange={handleFieldChange} required />
                  </label>

                  <label className="field">
                    <span className="field__label">Generic name</span>
                    <input
                      name="generic_name"
                      value={formState.generic_name}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Manufacturer</span>
                    <input
                      name="manufacturer"
                      value={formState.manufacturer}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Supplier</span>
                    <input
                      name="supplier_name"
                      value={formState.supplier_name}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Category</span>
                    <input
                      name="category"
                      value={formState.category}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Dosage form</span>
                    <input
                      name="dosage_form"
                      value={formState.dosage_form}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Strength</span>
                    <input
                      name="strength"
                      value={formState.strength}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Batch number</span>
                    <input
                      name="batch_number"
                      value={formState.batch_number}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Quantity</span>
                    <input
                      name="quantity"
                      type="number"
                      min="0"
                      value={formState.quantity}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Unit price</span>
                    <input
                      name="unit_price"
                      type="number"
                      min="0"
                      step="0.01"
                      value={formState.unit_price}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Reorder level</span>
                    <input
                      name="reorder_level"
                      type="number"
                      min="0"
                      value={formState.reorder_level}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field">
                    <span className="field__label">Expiry date</span>
                    <input
                      name="expiry_date"
                      type="date"
                      value={formState.expiry_date}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>

                  <label className="field field--full">
                    <span className="field__label">Storage location</span>
                    <input
                      name="location"
                      value={formState.location}
                      onChange={handleFieldChange}
                      required
                    />
                  </label>
                </div>

                <label className="checkbox-row">
                  <input
                    name="manual_expired"
                    type="checkbox"
                    checked={formState.manual_expired}
                    onChange={handleFieldChange}
                  />
                  <span>Mark this medicine as manually expired</span>
                </label>

                <div className="form-actions">
                  <button className="action-button" type="button" onClick={closeComposer}>
                    Cancel
                  </button>
                  <button className="action-button action-button--primary" type="submit" disabled={submitting}>
                    {submitting ? 'Saving...' : composerMode === 'create' ? 'Create Medicine' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </>
          ) : selectedMedicine ? (
            <>
              <div className="section-heading">
                <div>
                  <h2>{selectedMedicine.name}</h2>
                  <p>{selectedMedicine.generic_name}</p>
                </div>
                <StatusPill status={selectedMedicine.status} />
              </div>

              <dl className="detail-grid">
                <div>
                  <dt>Manufacturer</dt>
                  <dd>{selectedMedicine.manufacturer}</dd>
                </div>
                <div>
                  <dt>Supplier</dt>
                  <dd>{selectedMedicine.supplier_name}</dd>
                </div>
                <div>
                  <dt>Category</dt>
                  <dd>{selectedMedicine.category}</dd>
                </div>
                <div>
                  <dt>Dosage</dt>
                  <dd>
                    {selectedMedicine.dosage_form} | {selectedMedicine.strength}
                  </dd>
                </div>
                <div>
                  <dt>Batch</dt>
                  <dd>{selectedMedicine.batch_number}</dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>{selectedMedicine.location}</dd>
                </div>
                <div>
                  <dt>Expiry</dt>
                  <dd>{formatShortDate(selectedMedicine.expiry_date)}</dd>
                </div>
                <div>
                  <dt>Inventory value</dt>
                  <dd>{formatCurrency(selectedMedicine.stock_value)}</dd>
                </div>
                <div>
                  <dt>Quantity</dt>
                  <dd>{numberFormatter.format(selectedMedicine.quantity)}</dd>
                </div>
                <div>
                  <dt>Reorder level</dt>
                  <dd>{numberFormatter.format(selectedMedicine.reorder_level)}</dd>
                </div>
              </dl>

              <div className="inventory-note">
                {selectedMedicine.status === 'expired' || selectedMedicine.status === 'out_of_stock'
                  ? 'Use the update form to restock or refresh expiry details before bringing this medicine back into active sale.'
                  : 'This medicine is available for sale and can be edited or flagged from this panel.'}
              </div>

              <div className="detail-actions">
                <button
                  className="action-button action-button--primary"
                  type="button"
                  onClick={() => openEditComposer(selectedMedicine)}
                >
                  <AppIcon name="edit" />
                  Edit
                </button>
                <button
                  className="action-button"
                  type="button"
                  disabled={selectedMedicine.status === 'expired'}
                  onClick={() => handleStatusChange('expired')}
                >
                  Mark Expired
                </button>
                <button
                  className="action-button action-button--danger"
                  type="button"
                  disabled={selectedMedicine.status === 'out_of_stock'}
                  onClick={() => handleStatusChange('out_of_stock')}
                >
                  Mark Out of Stock
                </button>
              </div>
            </>
          ) : (
            <div className="empty-card">Select a medicine to view details.</div>
          )}
        </section>
      </div>
    </section>
  )
}

function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="header-actions">{actions}</div>
    </header>
  )
}

function MetricCard({ tone, icon, label, value, badge }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__header">
        <div className="metric-card__icon">
          <AppIcon name={icon} />
        </div>
        {badge ? <span className="metric-card__badge">{badge}</span> : null}
      </div>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  )
}

function StatusPill({ status, label }) {
  const text = label ?? prettifyStatus(status)
  return <span className={`status-pill status-pill--${status}`}>{text}</span>
}

function NoticeBanner({ tone, message }) {
  return <div className={`notice notice--${tone}`}>{message}</div>
}

function AppIcon({ name }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.8',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  }

  const icons = {
    search: (
      <>
        <circle cx="11" cy="11" r="6.5" {...common} />
        <path d="M16 16L20 20" {...common} />
      </>
    ),
    grid: (
      <>
        <rect x="4" y="4" width="6.5" height="6.5" rx="1.5" {...common} />
        <rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5" {...common} />
        <rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5" {...common} />
        <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5" {...common} />
      </>
    ),
    inventory: (
      <>
        <path d="M7 5.5H18.5V18.5H7Z" {...common} />
        <path d="M7 9H18.5" {...common} />
        <path d="M10 13H15.5" {...common} />
        <path d="M10 16H15.5" {...common} />
        <path d="M4.5 5.5V18.5" {...common} />
      </>
    ),
    menu: (
      <>
        <path d="M5 7H19" {...common} />
        <path d="M5 12H19" {...common} />
        <path d="M5 17H19" {...common} />
      </>
    ),
    pulse: <path d="M4 13H8L10.5 7L13.5 18L16 11H20" {...common} />,
    users: (
      <>
        <path d="M10 13.5C12.2091 13.5 14 11.7091 14 9.5C14 7.29086 12.2091 5.5 10 5.5C7.79086 5.5 6 7.29086 6 9.5C6 11.7091 7.79086 13.5 10 13.5Z" {...common} />
        <path d="M4.5 19C5.3 16.6 7.4 15.5 10 15.5C12.6 15.5 14.7 16.6 15.5 19" {...common} />
        <path d="M16.5 7C18.1 7.3 19.2 8.5 19.4 10.1" {...common} />
      </>
    ),
    stethoscope: (
      <>
        <path d="M8 5.5V10C8 12.2 9.8 14 12 14C14.2 14 16 12.2 16 10V5.5" {...common} />
        <path d="M6.5 5.5H9.5" {...common} />
        <path d="M14.5 5.5H17.5" {...common} />
        <path d="M16 13.5V16C16 18 17.6 19.5 19.5 19.5C20.9 19.5 22 18.4 22 17C22 15.6 20.9 14.5 19.5 14.5C18.1 14.5 17 15.6 17 17" {...common} />
      </>
    ),
    pill: (
      <>
        <path d="M8.5 15.5L15.5 8.5C17.4 6.6 20.4 6.6 22.3 8.5C24.2 10.4 24.2 13.4 22.3 15.3L15.3 22.3C13.4 24.2 10.4 24.2 8.5 22.3C6.6 20.4 6.6 17.4 8.5 15.5Z" transform="scale(.75) translate(-3 -3)" {...common} />
        <path d="M10 14L14 18" {...common} />
      </>
    ),
    plus: (
      <>
        <path d="M12 5V19" {...common} />
        <path d="M5 12H19" {...common} />
      </>
    ),
    spark: (
      <>
        <path d="M12 4L13.8 8.2L18 10L13.8 11.8L12 16L10.2 11.8L6 10L10.2 8.2L12 4Z" {...common} />
      </>
    ),
    settings: (
      <>
        <path d="M12 8.5C13.9 8.5 15.5 10.1 15.5 12C15.5 13.9 13.9 15.5 12 15.5C10.1 15.5 8.5 13.9 8.5 12C8.5 10.1 10.1 8.5 12 8.5Z" {...common} />
        <path d="M12 4.5V6.2M12 17.8V19.5M4.5 12H6.2M17.8 12H19.5M6.8 6.8L8 8M16 16L17.2 17.2M6.8 17.2L8 16M16 8L17.2 6.8" {...common} />
      </>
    ),
    sales: (
      <>
        <circle cx="9" cy="18" r="1.5" {...common} />
        <circle cx="17" cy="18" r="1.5" {...common} />
        <path d="M4 5H6L8.2 14H18L20 8H9" {...common} />
      </>
    ),
    purchase: (
      <>
        <path d="M7 4.5H15L19 8.5V19.5H7Z" {...common} />
        <path d="M15 4.5V8.5H19" {...common} />
        <path d="M10 12H16" {...common} />
        <path d="M10 15.5H14" {...common} />
      </>
    ),
    export: (
      <>
        <path d="M12 4V14" {...common} />
        <path d="M8 10L12 14L16 10" {...common} />
        <path d="M5 19H19" {...common} />
      </>
    ),
    warning: (
      <>
        <path d="M12 5L20 19H4L12 5Z" {...common} />
        <path d="M12 10V13.5" {...common} />
        <path d="M12 16.5H12.01" {...common} />
      </>
    ),
    box: (
      <>
        <path d="M12 3L19 7V17L12 21L5 17V7L12 3Z" {...common} />
        <path d="M5 7L12 11L19 7" {...common} />
        <path d="M12 11V21" {...common} />
      </>
    ),
    money: (
      <>
        <rect x="4.5" y="6.5" width="15" height="11" rx="2.5" {...common} />
        <path d="M12 9V15.5" {...common} />
        <path d="M14.5 10C13.9 9.3 13 9 12 9C10.4 9 9.5 9.8 9.5 11C9.5 12.3 10.6 12.8 12 13.1C13.4 13.4 14.5 13.8 14.5 15C14.5 16.2 13.4 17 12 17C10.8 17 9.7 16.6 9 15.8" {...common} />
      </>
    ),
    edit: (
      <>
        <path d="M4 20H8L18 10C19.1 8.9 19.1 7.1 18 6C16.9 4.9 15.1 4.9 14 6L4 16V20Z" {...common} />
        <path d="M12.5 7.5L16.5 11.5" {...common} />
      </>
    ),
    refresh: (
      <>
        <path d="M19 12A7 7 0 1 1 16.9 6.9" {...common} />
        <path d="M19 5V10H14" {...common} />
      </>
    ),
    check: (
      <>
        <path d="M5.5 12.5L9.5 16.5L18.5 7.5" {...common} />
      </>
    ),
  }

  return (
    <svg className="app-icon" viewBox="0 0 24 24" aria-hidden="true">
      {icons[name]}
    </svg>
  )
}

function formatCurrency(value) {
  return currencyFormatter.format(Number(value || 0))
}

function formatShortDate(value) {
  if (!value) {
    return '--'
  }

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))
}

function formatDateTime(value) {
  if (!value) {
    return '--'
  }

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function prettifyStatus(status) {
  if (!status) {
    return 'Unknown'
  }

  return status
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function extractApiError(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.message ||
    'Something went wrong while talking to the backend.'
  )
}

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  link.click()
  URL.revokeObjectURL(href)
}

function getDefaultExpiryDate() {
  const nextYear = new Date()
  nextYear.setFullYear(nextYear.getFullYear() + 1)
  return nextYear.toISOString().slice(0, 10)
}

function toMedicineFormState(medicine) {
  return {
    name: medicine.name,
    generic_name: medicine.generic_name,
    manufacturer: medicine.manufacturer,
    supplier_name: medicine.supplier_name,
    category: medicine.category,
    dosage_form: medicine.dosage_form,
    strength: medicine.strength,
    batch_number: medicine.batch_number,
    quantity: medicine.quantity,
    unit_price: medicine.unit_price,
    reorder_level: medicine.reorder_level,
    expiry_date: medicine.expiry_date,
    location: medicine.location,
    manual_expired: medicine.manual_expired,
  }
}

function toMedicinePayload(formState) {
  return {
    ...formState,
    quantity: Number(formState.quantity),
    unit_price: Number(formState.unit_price),
    reorder_level: Number(formState.reorder_level),
  }
}

export default App
