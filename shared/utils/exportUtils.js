import { normalizeDate } from "./helpers";

export const downloadCSV = (transactions) => {
    if (!transactions || transactions.length === 0) return;

    // 1. Define Headers
    const headers = ["Date", "Description", "Category", "Type", "Amount (INR)", "Bank", "Verified"];

    // 2. Convert Data to CSV Rows
    const rows = transactions.map(t => {
        // Use formatLocalDate for consistent YYYY-MM-DD or custom formatting
        const d = normalizeDate(t.date);
        const date = d ? d.toLocaleDateString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric' }) : 'Unknown';
        
        const rawDesc = String(t.description ?? t.title ?? t.label ?? '');
        const desc = `"${rawDesc.replace(/"/g, '""')}"`; // Escape quotes
        const cat = t.category || 'other';
        const type = t.type || '';
        
        // Ensure amount is a number and fallback to 0 only if truly invalid
        const rawAmt = t.amount ?? t.value ?? 0;
        const amt = Number.isFinite(parseFloat(rawAmt)) ? rawAmt : 0;
        
        const bank = t.bank || "N/A";
        const verified = (t.confidence != null && t.confidence > 0) ? "Yes" : "No";

        return [date, desc, cat, type, amt, bank, verified].join(",");
    });

    // 3. Combine Headers and Rows
    const csvContent = [headers.join(","), ...rows].join("\n");

    // 4. Create Blob and Link
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `Spendsy_Report_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    
    // 5. Trigger Download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
};