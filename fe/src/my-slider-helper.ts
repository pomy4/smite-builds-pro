// Just some stuff which could be in MySlider.vue,
// but it isn't very interesting and I don't want to
// keep scrolling by it when working on MySlider.vue.

import { SliderType } from "./types";

interface NumberProps {
  type: SliderType.Number;
  unparsedLimit: [number, number] | null;
  scale: number;
}

interface DateOrTimeProps {
  type: SliderType.Date | SliderType.Time;
  unparsedLimit: [string, string] | null;
}

export type OtherProps = NumberProps | DateOrTimeProps;

abstract class Helper {
  abstract nToS(n: number): string;
  abstract sToN(s: string): number;
  abstract default(): number;
  abstract step(): number;
  abstract width(): string;
}

class NumberHelper extends Helper {
  scale: number;
  constructor(scale: number) {
    super();
    this.scale = scale;
  }
  nToS(n: number): string {
    return n
      .toFixed(this.scale)
      .padStart(this.scale === 0 ? 2 : 3 + this.scale, "0");
  }
  sToN(s: string): number {
    return Number(s);
  }
  default(): number {
    return 0;
  }
  step(): number {
    return 1 / (this.scale + 1);
  }
  width(): string {
    return "6.667rem";
  }
}

class DateHelper extends Helper {
  nToS(n: number): string {
    return new Date(n).toISOString().split("T")[0];
  }
  sToN(s: string): number {
    const split = s.split("-");
    return Date.UTC(Number(split[0]), Number(split[1]) - 1, Number(split[2]));
  }
  default(): number {
    return Date.UTC(2012, 4, 31);
  }
  step(): number {
    return 1000 * 60 * 60 * 24;
  }
  width(): string {
    return "12rem";
  }
}

class TimeHelper extends Helper {
  nToS(n: number): string {
    return new Date(n).toISOString().split("T")[1].split(".")[0];
  }
  sToN(s: string): number {
    const split = s.split(":");
    return Date.UTC(
      0,
      0,
      1,
      Number(split[0]),
      Number(split[1]),
      Number(split[2])
    );
  }
  default(): number {
    return Date.UTC(0, 0);
  }
  step(): number {
    return 1000;
  }
  width(): string {
    return "9.3rem";
  }
}

export const helperFactory = (other: OtherProps) => {
  switch (other.type) {
    case SliderType.Number:
      return new NumberHelper(other.scale);
    case SliderType.Date:
      return new DateHelper();
    case SliderType.Time:
      return new TimeHelper();
  }
};
