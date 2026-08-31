'use client';

import type { Dispatch, SetStateAction } from 'react';
import type { PreviewOrder, CustomerPreview } from '../reportTypes';

type OrderField = keyof PreviewOrder;

type Props = {
  preview: CustomerPreview;
  editMode: boolean;
  setEditMode: Dispatch<SetStateAction<boolean>>;
  includedOrders: number;
  reviewedTotal: number;
  expected: number | null;
  variance: number | null;
  loading: boolean;
  money: Intl.NumberFormat;
  updateOrder: (index: number, field: OrderField, value: string | number | boolean) => void;
  generateReviewedInvoice: () => void;
};

export default function CustomerReview({
  preview,
  editMode,
  setEditMode,
  includedOrders,
  reviewedTotal,
  expected,
  variance,
  loading,
  money,
  updateOrder,
  generateReviewedInvoice,
}: Props) {
  return (
    <section className="review-card" aria-labelledby="review-title">
      <div className="review-heading">
        <div><p className="step-label">Pre-invoice review</p><h2 id="review-title">Verify {includedOrders} billed orders</h2></div>
        <label className="edit-toggle"><input type="checkbox" checked={editMode} onChange={(event) => setEditMode(event.target.checked)} /><span>Edit invoice data</span></label>
      </div>

      <div className="review-summary">
        <div><span>Included loads</span><strong>{includedOrders}</strong></div>
        <div><span>Reviewed total</span><strong>{money.format(reviewedTotal)}</strong></div>
        <div><span>Expected total</span><strong>{expected === null ? 'Not entered' : money.format(expected)}</strong></div>
      </div>

      <div className={variance === null || Math.abs(variance) > 0.01 ? 'variance-warning' : 'variance-warning matches'}>
        {variance === null && 'Enter an expected total above if you want an additional billing check.'}
        {variance !== null && Math.abs(variance) <= 0.01 && 'Totals match. The reviewed invoice agrees with the amount you expected.'}
        {variance !== null && variance > 0.01 && `${money.format(variance)} above expected. Check for duplicate orders, high linehaul/fuel values, or extra accessorial charges.`}
        {variance !== null && variance < -0.01 && `${money.format(Math.abs(variance))} below expected. Check for excluded or missing orders and missing charges.`}
      </div>

      <div className="order-table-wrap">
        <table className="order-review-table">
          <thead><tr><th>Use</th><th>Order / delivery movements</th><th>BOL / trailer</th><th>Linehaul</th><th>Fuel</th><th>Accessorials</th><th>Total</th></tr></thead>
          <tbody>
            {preview.orders.map((order, index) => {
              const accessorials = order.extra_drops + order.extra_pickups + order.other_charges;
              return (
                <tr key={`${order.company_id}-${order.order_id}`} className={order.included ? '' : 'excluded-row'}>
                  <td><input aria-label={`Include order ${order.order_id}`} type="checkbox" checked={order.included} onChange={(event) => updateOrder(index, 'included', event.target.checked)} /></td>
                  <td>
                    <strong>{order.company_id ? `${order.company_id} · ` : ''}{order.order_id}</strong>
                    <small>{order.origin} → {order.destination}</small>
                    <details className="movement-preview">
                      <summary>{order.stops.length} delivery {order.stops.length === 1 ? 'movement' : 'movements'}</summary>
                      <ol>
                        {order.stops.map((stop) => (
                          <li key={`${stop.company_id}-${stop.order_id}-${stop.movement_sequence}`}>
                            <b>{stop.consignee || 'Delivery location'}</b>
                            <span>{[stop.destination_city, stop.destination_state, stop.destination_zip].filter(Boolean).join(', ')}</span>
                          </li>
                        ))}
                      </ol>
                    </details>
                  </td>
                  <td>
                    {editMode ? <><input value={order.bol_number} onChange={(event) => updateOrder(index, 'bol_number', event.target.value)} /><input value={order.trailer_number} onChange={(event) => updateOrder(index, 'trailer_number', event.target.value)} /></> : <><span>{order.bol_number || 'No BOL'}</span><small>Trailer {order.trailer_number || '—'}</small></>}
                  </td>
                  {(['freight_charge', 'fuel_surcharge'] as const).map((field) => <td key={field}>{editMode ? <input className="money-input" type="number" step="0.01" value={order[field]} onChange={(event) => updateOrder(index, field, Number(event.target.value))} /> : money.format(order[field])}</td>)}
                  <td>{money.format(accessorials)}<small>{editMode ? 'Edit components below' : 'Drops, pickups & other'}</small>{editMode && <div className="mini-inputs">{(['extra_drops', 'extra_pickups', 'other_charges'] as const).map((field) => <input key={field} aria-label={field.replaceAll('_', ' ')} type="number" step="0.01" value={order[field]} onChange={(event) => updateOrder(index, field, Number(event.target.value))} />)}</div>}</td>
                  <td>{editMode ? <input className="money-input" type="number" step="0.01" value={order.total_charge} onChange={(event) => updateOrder(index, 'total_charge', Number(event.target.value))} /> : <strong>{money.format(order.total_charge)}</strong>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="review-footer">
        <p>Unchecked orders will not appear in the workbook. Edited values are used in both the invoice summary and load detail.</p>
        <button className="primary-button" type="button" onClick={generateReviewedInvoice} disabled={loading || includedOrders === 0}>{loading ? 'Generating…' : 'Generate reviewed invoice'}<span aria-hidden="true">→</span></button>
      </div>
    </section>
  );
}
