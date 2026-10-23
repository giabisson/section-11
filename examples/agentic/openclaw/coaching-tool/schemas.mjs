// Explicit transport schemas. Coaching/source/date/capacity/publication validation
// remains authoritative in the Python backend; no arbitrary object placeholders.
const text={type:'string',minLength:1,maxLength:4000};
const string={type:'string'};
const date={type:'string',pattern:'^\\d{4}-\\d{2}-\\d{2}$'};
const id={type:'string',pattern:'^[A-Za-z0-9_-]{1,64}$'};
const number={type:'number',minimum:0};
const positive={type:'number',exclusiveMinimum:0};
const boolean={type:'boolean'};
const definitions={};
const reference=(name,value)=>{definitions[name]=value;return {$ref:'#/$defs/'+name};};
const enumeration=values=>({type:'string',enum:values});
const nullable=value=>({anyOf:[value,{type:'null'}]});
const array=(items,limits={})=>({type:'array',items,...limits});
const strings=array(text);
const object=(properties,required=Object.keys(properties))=>({type:'object',additionalProperties:false,properties,required});
const evidence=array(object({source:text,as_of:date,summary:text}),{minItems:1});

export const feedbackSchema=object({date,state:enumeration(['rested','normal','fatigued','weak','symptoms','unknown']),note:text,
 health_clarification:nullable(object({compatible:boolean,reason:text}))});
const target={anyOf:[
 object({basis:enumeration(['ftp','ramp_peak_power','critical_power','watts']),low:number,high:number,
  zones:array({type:'integer',minimum:1,maximum:7},{minItems:1}),ramp:enumeration(['up','down'])},['basis','low','zones']),
 object({basis:enumeration(['max_effort']),zones:array({type:'integer',enum:[7]},{minItems:1,maxItems:1})})
]};
const step=object({role:enumeration(['warmup','work','endurance','recovery','set_recovery','cooldown']),seconds:{type:'integer',minimum:1},
 target,label:text,cadence_rpm:{type:'integer',minimum:1},technique:enumeration(['high_cadence','single_leg'])},['role','seconds','target']);
// The compiler permits at most four nested repeat blocks. A finite schema avoids
// recursive provider conversion and cannot imply that expanded dose is validated.
const leafStep=reference('step',step);
function steps(depth=0){return array(reference('step'+depth,depth===4?leafStep:{anyOf:[leafStep,object({repeat:{type:'integer',minimum:1,maximum:2000},steps:steps(depth+1)})]}),{minItems:1,maxItems:2000});}
const zoneBounds=object(Object.fromEntries(Array.from({length:7},(_,i)=>[String(i+1),array(number,{minItems:2,maxItems:2})])),[]);
const fitness=object({metric:enumeration(['ftp','ramp_peak_power','critical_power']),value_watts:positive,date:nullable(date),method:nullable(text),
 equipment:nullable(text),environment:nullable(enumeration(['indoor','outdoor','unknown'])),source:text,
 status:enumeration(['current','uncertain','stale','contradictory']),review_after:nullable(date),
 review:object({date,reason:text,decision:enumeration(['use_provisionally'])}),zone_bounds_watts:zoneBounds},
 ['metric','value_watts','source','status','zone_bounds_watts']);
const prescription=object({schema_version:{type:'integer',enum:[1]},session_template:text,template_version:text,available_minutes:positive,
 fitness_reference:fitness,sprint_reference:object({value_watts:positive,duration_seconds:{type:'integer',enum:[10]},date,source:text,
 set_targets_watts:array(positive,{minItems:3,maxItems:3})}),steps:steps()},
 ['schema_version','session_template','template_version','available_minutes','fitness_reference','steps']);
const workout=object({name:text,date,time:string,type:string,description:string,duration_minutes:positive,tss:number,target:nullable(string),
 category:string,indoor:boolean,color:text,synthetic:boolean,coaching_prescription:prescription},['name','date']);
const session={anyOf:[object({session_id:id,prescription_id:text}),
 object({session_id:id,purpose:text,alternatives:strings,session_budget_minutes:positive,workout})]};
const taper=object({start_date:date,end_date:date,reference_minutes:positive,planned_minutes:number,rationale:text,familiar_intensity:boolean});
const event=object({goal_id:id,expected_duration_minutes:nullable(positive),terrain:text,decisive_demands:array(text,{minItems:1}),
 recent_training_reference:evidence,taper:nullable(taper)});
const window=object({source:text,date,assessment:text,assessment_seconds:{type:'number',minimum:1},power_watts:positive,prior_minutes:nullable(number),
 prior_work:nullable(object({value:number,unit:enumeration(['kJ_mechanical'])})),prior_intensity:nullable(text),environment:nullable(text),
 pacing:nullable(text),fueling:nullable(text),conditions:nullable(text)});
const durability=object({fresh:nullable(window),fatigued:nullable(window),interpretation:text});
const strength=object({goal:text,experience:text,equipment:text,technique:text,soreness:text,arrangement:enumeration(['add','replace']),
 displaced_sessions:strings,recovery_plan:text,evidence_certainty:enumeration(['low'])});
const block=object({objective:text,goal_ids:array(id,{minItems:1}),planned_phase:text,start_date:date,end_date:date,starting_evidence:evidence,
 progression:text,recovery:text,review_date:date,change_conditions:array(text,{minItems:1}),event_preparation:nullable(event),
 durability_context:nullable(durability),strength_context:nullable(strength)},
 ['objective','goal_ids','planned_phase','start_date','end_date','starting_evidence','progression','recovery','review_date','change_conditions']);
export const planSchema=object({schema_version:{type:'integer',enum:[1]},planning_policy:enumeration(['athlete_specific_v1']),
 athlete_id:{type:'string',pattern:'^i?[0-9]+$'},plan_id:id,
 revision:object({request_id:id,parent_revision:nullable(text),reason:text,evidence}),
 goals:array(object({goal_id:id,description:text,priority:enumeration(['general','A','B','C']),date:nullable(date),
  demands:array(text,{minItems:1}),success_measure:text,constraints:strings}),{minItems:1}),block,
 weeks:array(object({start_date:date,weekly_minutes:number,session_windows:array(object({date,max_minutes:number})),
  intensity_approach:object({intent:text,zone_model:text,basis:text,rationale:text}),compromises:strings}),{minItems:1,maxItems:104}),
 sessions:array(session,{maxItems:1000}),detected_phase:nullable(object({value:text,as_of:date,source:text}))},
 ['schema_version','planning_policy','athlete_id','plan_id','revision','goals','block','weeks','sessions']);
const planReference=reference('plan',planSchema);
export const proposalSchema=object({current_athlete_context:object({date,source:text,goals_and_availability:text}),plan:planReference});
const observation=object({session_id:id,prescription_id:text,activity_id:{anyOf:[string,{type:'number'},{type:'null'}]},
 status:enumeration(['completed','modified','missed','unknown']),cause:enumeration(['none','work','availability','illness','injury','fatigue','equipment','preference','unknown']),
 goal_attainment:enumeration(['met','partial','not_met','unknown']),response:enumeration(['tolerated','unexpectedly_hard','adverse','unknown']),source:text,date,note:text});
const decision=object({action:enumeration(['maintain','progress','reduce','substitute','reschedule','request_context']),session_ids:strings,
 observation_ids:strings,reason:text,next_observation:text});
export const draftSchema=object({observations:array(observation),decisions:array(decision,{minItems:1}),candidate_plan:nullable(planReference)});
export const operationSchemas={
 state:object({operation:enumeration(['state'])}),
 feedback:object({operation:enumeration(['feedback']),payload:feedbackSchema}),
 propose:object({operation:enumeration(['propose']),payload:proposalSchema}),
 prepare:object({operation:enumeration(['prepare']),start:date,end:date}),
 save:object({operation:enumeration(['save']),capture_id:{type:'string',pattern:'^[a-f0-9]{64}$'},draft:draftSchema})
};
// Keep the provider-facing root an object. Runtime operation matching remains in
// requestFor/backend; payload alternatives expose both closed, typed contracts.
export const schema=object({operation:enumeration(Object.keys(operationSchemas)),
 payload:{anyOf:[feedbackSchema,proposalSchema]},start:date,end:date,
 capture_id:operationSchemas.save.properties.capture_id,draft:draftSchema},['operation']);

// Root-local definitions avoid repeating full plans and interval step shapes.
schema.$defs=definitions;
for(const operation of Object.values(operationSchemas))operation.$defs=definitions;
