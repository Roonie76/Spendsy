import { normalizeDate } from "./helpers";

export const downloadCSV = (transactions) => {
    if (!transactions || transactions.length === 0) return;

    // 1. Define Headers
    const headers = ["Date", "Description", "Category", "Type", "Amount (INR)", "Bank", "Verified"];

    // 2. Convert Data to CSV Rows
    const rows = transactions.map(t => {
        const date = normalizeDate(t.date).toLocaleDateString('en-IN');
        const desc = `"${t.description.replace(/"/g, '""')}"`; // Escape quotes
        const cat = t.category;
        const type = t.type;
        const amt = t.amount;
        const bank = t.bank || "N/A";
        const verified = t.confidence > 0 ? "Yes" : "No";
        
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