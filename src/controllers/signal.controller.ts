import { Controller } from '@nestjs/common';
import { EventPattern } from '@nestjs/microservices';
import { SignalService } from '../services/signal.service';

@Controller()
export class SignalController {
  constructor(private readonly signalService: SignalService) {}

  @EventPattern('trading.signal')
  async handleSignal(data: any) {
    try {
      const processedSignal = await this.signalService.processSignal(data);
      return processedSignal;
    } catch (error) {
      console.error('Error processing signal:', error);
      throw error;
    }
  }
} 