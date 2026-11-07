export type PrereqOperator = "AND" | "OR";

export interface PrereqGroup {
  operator: PrereqOperator;
  items: (string | PrereqGroup)[];
}

export interface Course {
  code: string;
  title: string;
  description: string;
  core_req: string[];
  pre_req: PrereqGroup | null;
}

export interface Node {
  code: string;
  data: Course | null;
  is_external: boolean;
}

export interface Edge {
  source: string; //code
  target: string; //code
  line_style: "solid" | "dashed";
}

export interface CourseGraph {
  nodes: Node[];
  edges: Edge[];
}