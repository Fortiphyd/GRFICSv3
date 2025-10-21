<script setup>
import { inject, ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";

const $api = inject("$api");

onMounted(async () => {});

</script>

<script>
import { toast } from "bulma-toast";
import {
  getHumanFriendlyTimeISO8601,
  b64DecodeUnicode,
} from "@/utils/utils";
export default {
  inject: ["$api"],
  data() {
    return {
        redOps: [],
        blueOps: [],
        hosts: [],
        allTactics: {},
        redOperation: {
            id: '',
            state: '',
            points: 0
        },
        blueOperation: {
            id: '',
            state: '',
            points: 0
        },
        access: '',
        dataExchanges: [],
        exchanges: {
            red: [],
            blue: []
        },
        modal: {
            isOpen: false,
            title: '',
            content: null,
        },
        stats: {
            true_pos: 0,
            false_pos: 0,
            false_neg: 0,
        },
        tactics: [],
        techniques: [],
        selectedHost: '',
        selectedTactic: '',
        selectedTechnique: '',
        detectByGuid: 1,
        detectionID: '',
        huntResults: '',
        linkOutput: '',
        analytic: {name: '', query: ''},
        expandQueries: false,
        generatedQueries: {}
    };
  },
  created() {
    this.initGameboard();
  },
  watch: {
    modal: {
      handler(newVal, oldVal) {
        if (newVal.content && newVal.content.unique && newVal.title == "Facts") {
          this.generatedQueries = this.generateQueries(newVal.content, this.access)
        }
      },
      deep: true,
    }
  },
  methods: {
    async initGameboard() {
        try {
            const res = await this.$api.get("/plugin/gameboard/ops");
            this.allTactics = res.data.tactics;
            this.hosts = res.data.hosts;
            this.redOps = res.data.red_ops;
            this.blueOps = res.data.blue_ops;
        } catch (error) {
          console.error(error);
        }
        if (this.allTactics) this.tactics = Object.keys(this.allTactics);
        setInterval(() => this.getGameboardData(), 3000);
    },
    async getGameboardData() {
        const render = (data) => {
            this.resetTables();
            this.redOperation.state = data.red_op_state;
            this.blueOperation.state = data.blue_op_state;
            this.redOperation.points = data.points[0];
            this.blueOperation.points = data.points[1];
            this.access = data.access;
            if (data.exchanges.length > 1) {
                this.dataExchanges = data.exchanges;
                this.exchanges.red = [];
                this.exchanges.blue = [];
                data.exchanges.forEach(([_, e]) => {
                    if (e.red) this.exchanges.red = this.exchanges.red.concat(e.red);
                    if (e.blue) this.exchanges.blue = this.exchanges.blue.concat(e.blue);
                });
                this.updateStats(this.exchanges);
            }
        };
        if (this.redOperation.id && this.blueOperation.id) {
            try {
                const res = await this.$api.post("/plugin/gameboard/pieces", {
                    red: this.redOperation.id,
                    blue: this.blueOperation.id
                });
                render(res.data);
            } catch (error) {
                console.error(error);
            }
        }
    },
    handleTacticChange() {
        if (this.selectedTactic && this.selectedTactic in this.allTactics) {
            this.techniques = this.allTactics[this.selectedTactic];
        } else {
            toast({
              message: "No techniques available for this tactic.",
              position: "bottom-right",
              type: "is-warning",
              dismissible: true,
              pauseOnHover: true,
              duration: 2000,
            });
        }
    },
    async handleSubmitDetection() {
        const submitDetectionCallback = (data) => {
            this.modal.isOpen = false;
            if (data.verified != false) {
                this.huntResults = `The information you entered matched correctly! Result:${data.message}`;
                toast({
                  message: this.huntResults,
                  position: "bottom-right",
                  type: "is-success",
                  dismissible: true,
                  pauseOnHover: true,
                  duration: 2000,
                });
            } else {
                this.huntResults = 'The information you entered did not match correctly.';
                toast({
                  message: this.huntResults,
                  position: "bottom-right",
                  type: "is-danger",
                  dismissible: true,
                  pauseOnHover: true,
                  duration: 2000,
                });
            }
        };
        try {
            const res = await this.$api.post("/plugin/gameboard/detection", {
                host: this.selectedHost,
                technique: this.selectedTechnique,
                verify: this.detectByGuid ? 'guid' : 'pid',
                info: this.detectionID,
                redOpId: this.redOperation.id,
                blueOpId: this.blueOperation.id,
            });
            submitDetectionCallback(res.data);
        } catch (error) {
            console.error(error);
        }
    },
    resetTables() {
        this.exchanges = {
            red: [],
            blue: []
        };
        this.stats = {
            true_pos: 0,
            false_pos: 0,
            false_neg: 0,
        };
    },
    async getOutput(linkID) {
        function loadResults(data) {
            return data.output ? b64DecodeUnicode(data.output) : '';
        }
        try {
            const res = await this.$api.post("/api/rest", {
                index: 'result',
                link_id: linkID
            });
            this.linkOutput = loadResults(res.data);
        } catch (error) {
            console.error(error);
        }
    },
    openModal(title, data = {}) {
        this.modal.title = title;
        if (data) this.modal.content = data;
        if (title.includes('Fact') && data.id) {
            this.getOutput(data.id);
        } else {
            this.linkOutput = '';
        }
        this.modal.isOpen = true;
    },
    updateStats(exchanges) {
        let T_P = 0;
        let F_P = 0;
        let F_N = 0;
        if (exchanges.red.length === 0) {
            F_P += exchanges.blue.length;
        } else if (exchanges.blue.length === 0) {
            F_N += exchanges.red.length;
        } else {
            T_P += exchanges.blue.length;
        }
        let total = T_P + F_P + F_N;
        this.stats.true_pos = Math.round((T_P / total) * 100);
        this.stats.false_pos = Math.round((F_P / total) * 100);
        this.stats.false_neg = Math.round((F_N / total) * 100);
    },
    async createAnalytic(analytic) {
        const handleAnalyticCallback = (data) => {
            this.modal.isOpen = false;
            toast({
              message: "Custom analytic created; Operation started.",
              position: "bottom-right",
              type: "is-success",
              dismissible: true,
              pauseOnHover: true,
              duration: 2000,
            });
        };
        try {
            const res = await this.$api.post("/plugin/gameboard/analytic", analytic);
            handleAnalyticCallback(res.data);
        } catch (error) {
            console.error(error);
        }
    },
    generateQueries(link, opType) {
        if (!link || !opType) return {};
        let splunkQueries = [];
        let elkQueries = [];
        if (opType === 'blue') {
            this.generateSpecific('ProcessId', link.pin, link.finish, splunkQueries, elkQueries);
            link.facts.forEach((fact) => {
                if (fact.trait === 'host.process.guid') {
                    this.generateSpecific('ProcessGuid', `"{ ${fact.value} }"`, link.finish);
                }
                if (fact.trait === 'host.process.recordid') {
                    this.generateSpecific('RecordNumber', fact.value, link.finish, splunkQueries, elkQueries);
                }
            });
        } else {
            this.generateSpecific('ProcessId', link.pid, link.finish, splunkQueries, elkQueries);
            this.generateSpecific('CommandLine', `"* ${b64DecodeUnicode(link.command).split(' ')[0]} *"`, link.finish, splunkQueries, elkQueries);
            if (link.executor.name === 'psh') {
                this.generateSpecific('CommandLine', '"*powershell*"', link.finish, splunkQueries, elkQueries);
            }
        }
        return {
            Splunk: splunkQueries,
            ELK: elkQueries
        };
    },
    generateSpecific(field, value, finish, splunkQueries, elkQueries) {
        splunkQueries.push(this.generateSplunkQuery(field, value, finish));
        elkQueries.push(this.generateELKQuery(field, value));
    },
    generateSplunkQuery(field, value, finish) {
        let earliest = this.incrementTime(finish, -5);
        let latest = this.incrementTime(finish, 5);
        return `source="XmlWinEventLog:Microsoft-Windows-Sysmon/Operational" ${field} = ${value} earliest="${earliest}" latest="${latest}" | table _time, Image, ProcessId, CommandLine, ParentProcessId, ParentProcessGuid, ParentCommandLine, User, Computer | sort _time`;
    },
    incrementTime(finishTime, increment) {
        let converted = new Date(finishTime);
        converted.setSeconds(converted.getSeconds() + increment);
        return this.formatSplunkTime(converted);
    },
    formatSplunkTime(time) {
        return `${time.getMonth() + 1}/${time.getDate()}/${time.getFullYear()}:${time.toString().split(' ')[4]}`;
    },
    generateELKQuery(field, value) {
        return `event_data.${field}: ${value}`;
    },
  },
}
</script>

<template lang="pug">
div(ref="gameboardHeader")
    h2
        | Gameboard
        sub.is-size-7.pl-1 red vs. blue exercises
    p
        | Monitor red-and-blue team operations during an exercise to see if blue can detect, respond, and
        | shut down a red-team adversary.
    hr
div#gameboardPage
    table.table.points-table.is-fullwidth
        thead
            tr
            th(colspan="2")
                .is-flex.is-flex-direction-column.is-align-items-flex-end
                    .is-flex.is-flex-direction-column.is-align-items-center
                        .is-flex.is-flex-direction-row.is-align-items-center.pb-2
                            div
                                em.fas.fa-user.pr-3.is-red-team.is-size-2(alt="Red team")
                            .is-flex.is-flex-direction-row.is-size-1
                                div(v-text="redOperation.points < 0 ? '-' : ''")
                                .points-card.has-background-black-ter.mr-2.py-1.px-2(alt="Red team points", v-text="Math.floor(Math.abs(redOperation.points / 10))")
                                .points-card.has-background-black-ter.py-1.px-2(alt="Red team points", v-text="Math.abs(redOperation.points % 10)")
                        label.mb-1.is-size-7(for="red-op-select") Operation
                        .select.is-small
                            select#red-op-select(v-model="redOperation.id", @change="getGameboardData")
                                option(value="") Select a red op
                                template(v-for="op in redOps", :key="op.id")
                                    option(:value="op.id", v-text="op.name + ' - ' + op.start")
                        label.is-size-7.mt-2(for="red-op-select", v-show="redOperation.state", :class="{'has-text-success': redOperation.state === 'running', 'has-text-warning': redOperation.state !== 'running'}", v-text="'is ' + redOperation.state")
            td(colspan="3")
                .is-flex.is-flex-direction-column.is-align-items-center
                    table.table.stats-table.my-5
                        thead
                        tr
                            th
                            th
                                span +
                            th
                                span -
                            th
                        tbody
                        tr
                            th T
                            td.is-blue-team.has-background-black(title="True Positive", v-text="stats.true_pos + '%'")
                            td.is-blue-team.has-background-black(title="True Negative") 0%
                            th T
                        tr
                            th F
                            td.is-red-team.has-background-black(title="False Positive", v-text="stats.false_pos + '%'")
                            td.is-red-team.has-background-black(title="False Negative", v-text="stats.false_neg + '%'")
                            th F
                    div
                        button.button.is-primary.is-small(@click="openModal('Analytic')")
                            em.fas.fa-pencil-alt.pr-1 Custom Analytic
            th(colspan="2")
                .is-flex.is-flex-direction-column.is-align-items-flex-start
                    .is-flex.is-flex-direction-column.is-align-items-center
                        .is-flex.is-flex-direction-column.is-align-items-center.pb-2
                            .is-flex.is-flex-direction-row.is-size-1
                                div(v-text="blueOperation.points < 0 ? '-' : ''")
                                .points-card.has-background-black-ter.mr-2.py-1.px-2(alt="Blue team points", v-text="Math.floor(Math.abs(blueOperation.points) / 10)")
                                .points-card.has-background-black-ter.py-1.px-2(alt="Blue team points", v-text="Math.abs(blueOperation.points % 10)")
                            label.mb-1.is-size-7(for="blue-op-select") Operation
                            .select.is-small
                                select#blue-op-select(v-model="blueOperation.id", @change="getGameboardData")
                                    option(value="") Select a blue op
                                    template(v-for="op in blueOps", :key="op.id")
                                        option(:value="op.id", v-text="op.name + ' - ' + op.start")
                            label.is-size-7.mt-2(for="blue-op-select", v-show="blueOperation.state", :class="{'has-text-success': blueOperation.state === 'running', 'has-text-warning': blueOperation.state !== 'running'}", v-text="'is ' + blueOperation.state")
                            template(v-if="exchanges.blue.length > 0")
                                div
                                    button.button.is-primary.is-blue-team.is-small.mt-3(@click="openModal('Add External Detection')")
                                        em.fas.fa-plus.pr-1 External Detection
            template(v-if="exchanges.blue.length < 1 && exchanges.red.length < 1")
                tbody
                tr
                    td.is-italic.has-text-centered(colspan="7") No exchanges to show.
            template(v-if="redOperation.id.length > 0 && blueOperation.id.length > 0 && exchanges.red && exchanges.blue")
                tbody
                template(v-for="(exchange, index) in dataExchanges", :key="'exchange-' + index")
                    tr.m-2
                        td(colspan="2")
                            div(v-show="exchange[1].red.length > 0", class="is-flex is-align-items-flex-end is-flex-direction-column")
                            template(v-for="redOp in exchange[1].red")
                                div.p-2.card.has-red-line.my-2.has-text-centered(@click="openModal('Facts', redOp)", :class="{'is-red-team': access === 'red', 'has-background-black-ter': access !== 'red'}")
                                    button.facts-link.has-text-white(v-text="redOp.ability.name")
                                    template(v-if="access === 'red'")
                                        div.is-flex.is-flex-direction-column.align-center
                                            span(v-text="getHumanFriendlyTimeISO8601(redOp.finish)")
                                            span.is-italic(v-text="redOp.paw")
                                    template(v-if="access === 'blue'")
                                        span.is-italic(v-text="redOp.ability.technique_id")
                                    span.facts-star(v-show="access === 'red' && redOp.facts.length > 0")
                                        em.fas.fa-star
                        td.is-size-2.is-red-team.is-flex.is-justify-content-flex-end(colspan="1")
                            template(v-for="redOp in exchange[1].red")
                                div.is-red-team.points-container.p-2.mt-4.mb-5
                                    span.points-text(v-text="redOp.points.value >= 0 ? '+' + redOp.points.value : redOp.points.value")
                        td.process-column(colspan="1")
                            template(v-if="exchange[1].red.length > 0 && exchange[1].blue.length > 0")
                                div.has-background-black-ter.points-card.has-text-centered.px-5.py-3(title="Process ID")
                                    p.mb-0.is-size-7.has-background-black-ter pid
                                    p.is-italic.is-size-6.has-background-black-ter(v-text="exchange[0]")
                        td.is-size-2.is-blue-team(colspan="1")
                            template(v-for="blueOp in exchange[1].blue")
                                div.is-blue-team.points-container.p-2.mt-4.mb-5
                                    span.points-text(v-text="blueOp.points.value >= 0 ? '+' + blueOp.points.value : blueOp.points.value")
                        td(colspan="2")
                            template(v-if="exchange[1].blue.length > 0 && exchange[1].blue[0].finish")
                                div.is-flex.is-justify-content-flex-start.is-flex-direction-column
                                template(v-for="blueOp in exchange[1].blue")
                                    div.p-2.my-2.card.has-blue-line.has-text-centered(@click="openModal('Facts', blueOp)", :class="{'is-blue-team': access === 'blue', 'has-background-black-ter': access !== 'blue'}")
                                        template(v-if="access === 'red'")
                                            span.is-italic(v-text="blueOp.ability && blueOp.ability.name ? blueOp.ability.name : 'Click for more details.'")
                                        template(v-if="access === 'blue'")
                                            div.is-flex.is-flex-direction-column.is-align-items-center
                                                span.is-italic(v-text="blueOp.ability && blueOp.ability.name ? blueOp.ability.name : 'Click for more details.'")
                                                span(v-text="blueOp.finish ? getHumanFriendlyTimeISO8601(blueOp?.finish) : ''")
                                                span.is-italic(v-text="blueOp?.paw")
                                        span.facts-star(v-show="access === 'blue' && blueOp?.facts?.length > 0")
                                            em.fas.fa-star

// MODAL
template(v-if="modal.isOpen")
    .modal.is-active
        .modal-background(@click="modal.isOpen = false; modal.content = {}")
        .modal-card
            header.modal-card-head
                p.modal-card-title(v-text="modal.title")
            section.modal-card-body
                template(v-if="modal.title.includes('Analytic')")
                    div
                        .modal-form
                            div
                                label(for="analytic-name") Analytic name
                                .modal-form-fields
                                    input.input.is-small(id="analytic-name", v-model="analytic.name" required)
                            div
                                label(for="analytic-query") Query
                                .modal-form-fields
                                    input.input.is-small(id="analytic-query", v-model="analytic.query" required)
                template(v-if="modal.title.includes('Detection')")
                    div
                        .modal-form
                            div
                                label(for="host-select") Host
                                .modal-form-fields
                                    .select.is-small.my-2.ml-3
                                        select#host-select(v-model="selectedHost")
                                            option(value="") Select a host
                                            template(v-for="host in hosts", :key="host")
                                                option(:value="host") {{ host }}
                            div
                                label(for="tactic-select") Tactic
                                .modal-form-fields
                                    .select.is-small.my-2.ml-3
                                        select#tactic-select(v-model="selectedTactic", @change="handleTacticChange()")
                                            option(value="") Select a tactic
                                            template(v-for="tactic in tactics", :key="tactic")
                                                option(v-text="tactic")
                            div
                                label(for="technique-select") Technique
                                .modal-form-fields
                                    .select.is-small.my-2.ml-3
                                        select#technique-select(v-model="selectedTechnique")
                                            option(value="") Select a technique
                                            template(v-for="technique in techniques", :key="technique[0]")
                                                option(v-text="technique[0] + ': ' + technique[1]")
                            div
                                label(for="detection-id-input" v-tooltip="'In order to add a manual Sysmon GUID detection, a blue agent must have been running on the target system during the red operation.'")
                                    span.has-tooltip-multiline.has-tooltip-right
                                    | Detect-by ID
                                .modal-form-fields.pl-2#detection-id-choice
                                    input(type="radio", id="detection-by-pid", :checked="detectByGuid === 0" @click="detectByGuid = 0")
                                    label(for="detection-by-pid") pid
                                    input(type="radio", id="detection-by-guid", :checked="detectByGuid === 1" @click="detectByGuid = 1")
                                    label(for="detection-by-guid") guid
                            div
                                label(v-show="detectByGuid == '0'", for="detection-id-choice") pid
                                label(v-show="detectByGuid == '1'", for="detection-id-choice") guid
                                .modal-form-fields
                                    input#detection-id-input.mt-4.ml-4.input.is-small(v-model="detectionID")
                template(v-if="modal.title.includes('Facts') && modal.content")
                    div
                        template(v-if="modal.content.unique")
                            div
                                .modal-form
                                    template(v-if="modal.content.unique")
                                        div
                                            label(for="fact-unique") Unique
                                            .modal-form-fields
                                                input.input.is-small(id="fact-unique", :value="modal.content.unique" readonly)
                                    template(v-if="modal.content.ability && modal.content.ability.technique_id && modal.content.ability.technique_name")
                                        div
                                            label(for="fact-command") Command
                                            .modal-form-fields
                                                input.input.is-small(id="fact-command", :value="modal.content.ability.technique_id + ': ' + modal.content.ability.technique_name" readonly)
                                    template(v-if="modal.content.output")
                                        div
                                            label(for="fact-output") Output
                                            .modal-form-fields(v-show="modal.content.output !== 'False'")
                                                input.input.is-small(id="fact-output", :value="linkOutput" readonly)
                                            .modal-form-fields(v-show="modal.content.output === 'False'")
                                                input.input.is-italic.is-small(id="fact-output", :value="'No output'" readonly)
                        template(v-if="modal.content.points && modal.content.points.reason")
                            div
                                .modal-form
                                    div
                                        label(for="fact-reason") Reason
                                        .modal-form-fields
                                            input.input.is-small(id="fact-reason", :value="modal.content.points.reason" readonly)
                        template(v-if="modal.content.unique")
                            div
                                .modal-form-group-header
                                    button.button.no-style.heading.pt-2(@click="expandQueries = !expandQueries", :class="expandQueries ? 'expanded' : 'collapsed'")
                                        span Suggested Queries
                                            em.fas.fa-caret-right(v-show="!expandQueries")
                                            em.fas.fa-caret-down(v-show="expandQueries")
                                        span.navbar-divider
                                .modal-form(v-show="expandQueries")
                                    template(v-if="generatedQueries && generatedQueries.ELK && generatedQueries.ELK.length > 0")
                                        div
                                            label(for="fact-elk-queries") ELK Queries
                                            .modal-form-fields#fact-elk-queries
                                                template(v-for="(query, index) in generatedQueries.ELK", :key="'query-elk-' + index")
                                                    input.input.is-small.m-2(:value="query" readonly)
                                    template(v-if="generatedQueries && generatedQueries.Splunk && generatedQueries.Splunk.length > 0")
                                        div
                                            label(for="fact-splunk-queries") Splunk Queries
                                            .modal-form-fields#fact-splunk-queries
                                                template(v-for="(query, index) in generatedQueries.Splunk", :key="'query-splunk-' + index")
                                                    textarea.textarea.m-2(:value="query" readonly)
            footer.modal-card-foot
                nav.level
                    .level-left
                        template(v-if="!modal.title.includes('Facts')")
                            .level-item
                                button.button.is-small(@click="modal.isOpen = false") Cancel
                        template(v-if="modal.title.includes('Facts')")
                            .level-item
                                button.button.is-small(@click="modal.isOpen = false; modal.content = {}") Close
                    .level-right
                        template(v-if="access === 'red' && modal.title.includes('Facts')")
                            button.button.is-small.is-primary(@click="modal.isOpen = false; openModal('Analytic')") Create Analytic
                        template(v-if="modal.title.includes('Analytic')")
                            button.button.is-small.is-primary(@click="createAnalytic(analytic)") Save
                        template(v-if="modal.title.includes('Detection')")
                            button.button.is-small.is-primary(@click="handleSubmitDetection()") Submit
</template>

<style>
    #gameboardPage .is-red-team {
        color: #ea1543;
    }

    #gameboardPage .is-blue-team {
        color: #4C4CF2;
    }

    #gameboardPage .modal-form-fields code {
        overflow-y: scroll;
        max-height: 500px;
        word-break: break-word;
    }

    #gameboardPage .facts-star {
        position: absolute;
        top: 8px;
        right: 8px;
    }

    #gameboardPage .process-column div p:first-child:before {
        width: 2px;
        height: 72px;
        background-color: #242424;
        content: "";
        display: inline-block;
        position: absolute;
        margin-left: 7px;
        margin-top: 42px;
    }

    #gameboardPage button.no-style {
        background-color: transparent;
        border: none;
        box-shadow: none;
    }

    #gameboardPage .points-card {
        border-radius: 5px;
    }

    #gameboardPage .card {
        cursor: pointer;
        border-radius: 2px;
        color: white;
        width: 315px;
        height: 80px;
    }

    #gameboardPage .card.is-red-team, #gameboardPage .points-container.is-red-team {
        background-color: #ea1543;
    }

    #gameboardPage button.is-blue-team, #gameboardPage .card.is-blue-team, #gameboardPage .points-container.is-blue-team {
        background-color: #4C4CF2;
        color: white;
    }

    #gameboardPage .card.has-red-line:after {
        background: #ea1543;
        content: "";
        width: 15%;
        height: 3px;
        display: flex;
        position: absolute;
        z-index: 0;
        transform: translate(181px, -5px);
    }

    #gameboardPage .card.has-blue-line:before {
        background: #4C4CF2;
        content: "";
        width: 15%;
        height: 3px;
        display: flex;
        position: absolute;
        z-index: 0;
        transform: translate(-181px, -5px);
    }

    #gameboardPage .points-container {
        border-radius: 50px;
        color: white;
        width: 65px;
        text-align: center;
    }

    #gameboardPage .facts-link {
        line-height: 1.5em;
        border: none;
        background-color: transparent;
        font-size: 1em;
        text-decoration: underline;
    }
    #gameboardPage .table {
      background-color: #161616 !important;
    }

    #gameboardPage .stats-table {
        max-width: 100px;
    }

    #gameboardPage .stats-table th, #gameboardPage .stats-table td {
        text-align: center;
    }

    #gameboardPage .stats-table tr:not(:last-child) td {
        border-bottom: 2px solid #ffffffa1 !important;
    }

    #gameboardPage .stats-table td:nth-child(2) {
        border-right: 2px solid #ffffffa1 !important;
    }

    #gameboardPage .points-table thead th {
        width: 40%;
        border-bottom: none;
    }

    #gameboardPage .points-table tr, #gameboardPage .points-table td {
        border: none;
    }

    #gameboardPage .points-table tr, #gameboardPage .points-table td {
        vertical-align: middle !important;
    }
</style>
