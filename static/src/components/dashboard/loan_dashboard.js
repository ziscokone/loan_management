/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DateRangePicker } from "@web/core/datetime/datetime_picker";

class LoanDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            approvedCount: 0,
            rejectedCount: 0,
            pendingCount: 0,
            totalRequestedAmount: 0,
            totalApprovedAmount: 0,
            loading: true,
            startDate: null,
            endDate: null,
            selectedPeriod: 'all'
        });

        onWillStart(async () => {
            await this.fetchDashboardData();
        });
    }

    getDateRange(period) {
        const today = new Date();
        const startDate = new Date();
        let endDate = new Date();

        switch (period) {
            case 'today':
                startDate.setHours(0, 0, 0, 0);
                endDate.setHours(23, 59, 59, 999);
                break;
            case 'week':
                startDate.setDate(today.getDate() - today.getDay());
                startDate.setHours(0, 0, 0, 0);
                endDate.setHours(23, 59, 59, 999);
                break;
            case 'month':
                startDate.setDate(1);
                startDate.setHours(0, 0, 0, 0);
                endDate.setHours(23, 59, 59, 999);
                break;
            case 'year':
                startDate.setMonth(0, 1);
                startDate.setHours(0, 0, 0, 0);
                endDate.setHours(23, 59, 59, 999);
                break;
            case 'custom':
                return {
                    startDate: this.state.startDate,
                    endDate: this.state.endDate
                };
            default:
                return { startDate: false, endDate: false };
        }

        return { startDate, endDate };
    }

    async onPeriodChange(ev) {
        const period = ev.target.value;
        this.state.selectedPeriod = period;
        if (period !== 'custom') {
            await this.fetchDashboardData();
        }
    }

    async onDateRangeChange(range) {
        this.state.startDate = range.start;
        this.state.endDate = range.end;
        this.state.selectedPeriod = 'custom';
        await this.fetchDashboardData();
    }

    getDomain() {
        const { startDate, endDate } = this.getDateRange(this.state.selectedPeriod);
        const domain = [];

        if (startDate && endDate) {
            domain.push(['create_date', '>=', startDate]);
            domain.push(['create_date', '<=', endDate]);
        }

        return domain;
    }

    async fetchDashboardData() {
        this.state.loading = true;
        try {
            const domain = this.getDomain();
            const [counts, amounts] = await Promise.all([
                this.fetchApplicationCounts(domain),
                this.fetchAmountStats(domain),
            ]);

            Object.assign(this.state, {
                ...counts,
                ...amounts,
                loading: false,
            });
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
            this.state.loading = false;
        }
    }

    async fetchApplicationCounts(domain) {
        const [approved, rejected, pending] = await Promise.all([
            this.orm.searchCount("loan.application", [...domain, ["state", "=", "validated"]]),
            this.orm.searchCount("loan.application", [...domain, ["state", "=", "rejected"]]),
            this.orm.searchCount("loan.application", [...domain, ["state", "=", "pending"]]),
        ]);

        return {
            approvedCount: approved,
            rejectedCount: rejected,
            pendingCount: pending,
        };
    }

    async fetchAmountStats(domain) {
        const stats = await this.orm.call(
            "loan.application",
            "get_amounts_stats",
            [domain],
        );

        return {
            totalRequestedAmount: stats.total_requested,
            totalApprovedAmount: stats.total_approved,
        };
    }

    static template = "loan_management.LoanDashboard";
    static components = { DateRangePicker };
}

// Register the component
registry.category("actions").add("loan_dashboard_action", LoanDashboard);

export default LoanDashboard;